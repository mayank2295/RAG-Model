"""
News & Jobs RAG Chatbot — FastAPI server.

Endpoints:
    GET  /            → chat UI
    POST /api/chat    → SSE streaming answer grounded in news + jobs context
    POST /api/ingest  → manually trigger a news + jobs fetch
    GET  /api/status  → last ingest time + vector counts per namespace

An APScheduler BackgroundScheduler runs the ingest every 6 hours. An initial
ingest runs once at startup. All configuration comes from environment
variables — there is no local file storage anywhere.

Environment variables:
    PINECONE_API_KEY, PINECONE_INDEX, NEWSAPI_KEY, OPENROUTER_API_KEY
"""

import json
import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAI
from pydantic import BaseModel

import embedder
import vector_store
from jobs_fetcher import fetch_and_ingest_jobs
from news_fetcher import fetch_and_ingest_news

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("server")

# Force UTF-8 stdout/stderr so Unicode logs don't crash on Windows.
for _stream in (sys.stdout, sys.stderr):
    if _stream and getattr(_stream, "encoding", "").lower() != "utf-8":
        try:
            _stream.reconfigure(encoding="utf-8")
        except Exception:
            pass

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
LLM_MODEL = "anthropic/claude-3-haiku"
INGEST_INTERVAL_HOURS = 6

SYSTEM_PROMPT = (
    "You are a helpful assistant with access to today's latest news and job "
    "openings. Answer questions based on the provided context. If the context "
    "does not contain the answer, say so clearly."
)

# Runtime status, kept in memory (no disk).
_status = {
    "last_ingest_started": None,
    "last_ingest_finished": None,
    "last_news_count": None,
    "last_jobs_count": None,
    "ingest_running": False,
}

_scheduler: BackgroundScheduler | None = None


def _openrouter_client() -> OpenAI:
    """Build an OpenRouter-compatible OpenAI client from env config."""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY environment variable is not set.")
    return OpenAI(base_url=OPENROUTER_BASE_URL, api_key=api_key)


def run_ingest() -> dict:
    """
    Run a full news + jobs ingest cycle and update the in-memory status.

    Returns:
        Dict with the counts ingested for each namespace.
    """
    if _status["ingest_running"]:
        logger.warning("Ingest already running — skipping this trigger.")
        return {"skipped": True}

    _status["ingest_running"] = True
    _status["last_ingest_started"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    try:
        logger.info("=== Ingest cycle starting ===")
        news_count = fetch_and_ingest_news()
        jobs_count = fetch_and_ingest_jobs()
        _status["last_news_count"] = news_count
        _status["last_jobs_count"] = jobs_count
        _status["last_ingest_finished"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        logger.info("=== Ingest cycle done — news=%d jobs=%d ===", news_count, jobs_count)
        return {"news": news_count, "jobs": jobs_count}
    finally:
        _status["ingest_running"] = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Warm up the embedder, run an initial ingest, and start the scheduler."""
    global _scheduler

    embedder.warm_up()

    # Initial ingest at startup (best-effort — server still boots on failure).
    try:
        run_ingest()
    except Exception:
        logger.exception("Initial ingest failed — server will continue and retry on schedule.")

    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.add_job(
        run_ingest,
        trigger="interval",
        hours=INGEST_INTERVAL_HOURS,
        id="periodic_ingest",
        max_instances=1,
        coalesce=True,
    )
    _scheduler.start()
    logger.info("Scheduler started — ingest every %d hours.", INGEST_INTERVAL_HOURS)

    yield

    if _scheduler:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped.")


app = FastAPI(title="News & Jobs RAG Chatbot", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_STATIC_DIR = Path(__file__).parent / "static"
if _STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")


# ── Frontend ────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    """Serve the chat UI."""
    index_path = _STATIC_DIR / "index.html"
    if not index_path.exists():
        return HTMLResponse("<h1>News & Jobs RAG Chatbot</h1><p>UI not found.</p>")
    return HTMLResponse(index_path.read_text(encoding="utf-8"))


# ── Status + manual ingest ────────────────────────────────────────────────────

@app.get("/api/status")
async def status():
    """Return last ingest time and vector counts for both namespaces."""
    counts = vector_store.namespace_counts()
    return {
        "last_ingest_started": _status["last_ingest_started"],
        "last_ingest_finished": _status["last_ingest_finished"],
        "last_news_count": _status["last_news_count"],
        "last_jobs_count": _status["last_jobs_count"],
        "ingest_running": _status["ingest_running"],
        "vector_counts": counts,
        "ingest_interval_hours": INGEST_INTERVAL_HOURS,
    }


@app.post("/api/ingest")
async def ingest():
    """Manually trigger a news + jobs ingest cycle (runs synchronously)."""
    result = run_ingest()
    if result.get("skipped"):
        raise HTTPException(status_code=409, detail="Ingest already in progress.")
    return {"status": "ok", **result}


# ── Chat ───────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    """Body for POST /api/chat."""
    message: str
    top_k: int = 5


def _format_context(matches: list[dict]) -> str:
    """Format Pinecone matches into a readable context block for the LLM."""
    lines: list[str] = []
    for m in matches:
        md = m.get("metadata", {})
        ns = m.get("namespace")
        if ns == "news":
            lines.append(
                f"[NEWS] {md.get('title', '')} "
                f"(source: {md.get('source', 'Unknown')}, {md.get('publishedAt', '')})\n"
                f"{md.get('description', '')}\nURL: {md.get('url', '')}"
            )
        elif ns == "jobs":
            lines.append(
                f"[JOB] {md.get('title', '')} at {md.get('company', '')} "
                f"({md.get('published_date', '')})\n"
                f"Tags: {', '.join(md.get('tags', []))}\nURL: {md.get('url', '')}"
            )
        else:
            lines.append(json.dumps(md))
    return "\n\n---\n\n".join(lines) if lines else "No relevant context found."


@app.post("/api/chat")
async def chat(req: ChatRequest):
    """
    Answer a question grounded in the latest news + job context, streamed via SSE.

    Pipeline: embed query → query both namespaces → format context →
    OpenRouter chat completion → stream tokens as Server-Sent Events.
    """
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    if len(req.message) > 4000:
        raise HTTPException(status_code=400, detail="Message exceeds 4000 characters.")
    top_k = max(1, min(req.top_k, 20))

    query_vector = embedder.embed_text(req.message)
    matches = vector_store.query_all_namespaces(query_vector, top_k=top_k)
    context = _format_context(matches)

    sources = [
        {"namespace": m.get("namespace"), "score": m.get("score"), "metadata": m.get("metadata", {})}
        for m in matches
    ]

    client = _openrouter_client()
    user_content = f"CONTEXT:\n{context}\n\nQUESTION: {req.message}"

    def event_stream():
        yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"
        try:
            stream = client.chat.completions.create(
                model=LLM_MODEL,
                max_tokens=1024,
                stream=True,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
            )
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    token = chunk.choices[0].delta.content
                    yield f"data: {json.dumps({'type': 'token', 'text': token})}\n\n"
        except Exception as e:
            logger.exception("LLM streaming failed.")
            yield f"data: {json.dumps({'type': 'error', 'text': str(e)})}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "10000"))
    uvicorn.run("server:app", host="0.0.0.0", port=port)
