"""
FastAPI server — RAG pipeline + chat UI.

Endpoints:
  GET  /              → chat UI
  POST /api/chat      → SSE streaming answer
  GET  /api/health    → health + chunk count
  GET  /api/models    → available LLM list
  GET  /api/documents → indexed sources + stats
  GET  /api/stats     → full knowledge base stats
  POST /api/rebuild   → hot-reload the knowledge base from disk
"""

import json
import os
import asyncio
import time
from pathlib import Path
from contextlib import asynccontextmanager
from collections import defaultdict

from openai import OpenAI
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from document_loader import load_documents
from embedder import Embedder
from vector_store import VectorStore


OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
if not OPENROUTER_API_KEY:
    import sys
    print("ERROR: OPENROUTER_API_KEY environment variable is not set.")
    print("  Copy .env.example to .env and add your key from https://openrouter.ai/keys")
    sys.exit(1)
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

AVAILABLE_MODELS = [
    {"id": "google/gemma-4-31b-it:free",             "name": "Gemma 4 31B",   "provider": "Google"},
    {"id": "meta-llama/llama-3.3-70b-instruct:free", "name": "Llama 3.3 70B", "provider": "Meta"},
    {"id": "mistralai/mistral-7b-instruct:free",      "name": "Mistral 7B",    "provider": "Mistral"},
    {"id": "meta-llama/llama-3.2-3b-instruct:free",  "name": "Llama 3.2 3B",  "provider": "Meta"},
    {"id": "qwen/qwen-2.5-7b-instruct:free",         "name": "Qwen 2.5 7B",   "provider": "Qwen"},
]

rag_state: dict = {}


def _build_kb():
    """Load documents, embed, and populate rag_state."""
    t0 = time.time()
    print("\n=== Building Knowledge Base ===")
    chunks = load_documents("documents", chunk_size=500, overlap=80)
    embedder = rag_state.get("embedder") or Embedder()
    embeddings = embedder.embed([c.text for c in chunks])
    store = VectorStore(embedding_dim=embeddings.shape[1])
    store.add(chunks, embeddings)
    elapsed = time.time() - t0

    # Category breakdown
    cats: dict = defaultdict(int)
    for c in chunks:
        top = c.source.split("/")[0]
        cats[top] += 1

    rag_state.update({
        "chunks": chunks,
        "embedder": embedder,
        "store": store,
        "built_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "build_seconds": round(elapsed, 1),
        "categories": dict(cats),
        "client": OpenAI(base_url=OPENROUTER_BASE_URL, api_key=OPENROUTER_API_KEY),
    })
    print(f"=== Knowledge Base Ready — {len(chunks):,} chunks in {elapsed:.1f}s ===\n")


@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _build_kb)
    yield
    rag_state.clear()


app = FastAPI(title="RAG Chatbot", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")


# ── Frontend ──────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


# ── Info endpoints ─────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "chunks_indexed": len(rag_state.get("chunks", [])),
        "built_at": rag_state.get("built_at"),
    }


@app.get("/api/models")
async def list_models():
    return {"models": AVAILABLE_MODELS}


@app.get("/api/documents")
async def list_documents():
    chunks = rag_state.get("chunks", [])
    sources = sorted({c.source for c in chunks})
    return {"documents": sources, "total_chunks": len(chunks)}


@app.get("/api/stats")
async def knowledge_base_stats():
    chunks = rag_state.get("chunks", [])
    docs_dir = Path("documents")

    # File counts per category
    file_counts: dict = defaultdict(int)
    for p in docs_dir.rglob("*"):
        if p.is_file() and p.suffix.lower() in (".txt", ".csv", ".json", ".jsonl"):
            top = p.relative_to(docs_dir).parts[0] if len(p.relative_to(docs_dir).parts) > 1 else "root"
            file_counts[top] += 1

    total_size_mb = sum(
        p.stat().st_size for p in docs_dir.rglob("*") if p.is_file()
    ) / 1024 / 1024 if docs_dir.exists() else 0

    return {
        "total_chunks": len(chunks),
        "total_files": sum(file_counts.values()),
        "total_size_mb": round(total_size_mb, 2),
        "categories": dict(sorted(file_counts.items())),
        "chunk_categories": rag_state.get("categories", {}),
        "built_at": rag_state.get("built_at"),
        "build_seconds": rag_state.get("build_seconds"),
    }


# ── Rebuild endpoint ───────────────────────────────────────────────────────────

_rebuild_lock = asyncio.Lock()
_rebuild_status = {"running": False, "last": None}


@app.post("/api/rebuild")
async def rebuild_kb(background_tasks: BackgroundTasks):
    """Hot-reload the knowledge base from disk without restarting the server."""
    if _rebuild_status["running"]:
        raise HTTPException(status_code=409, detail="Rebuild already in progress.")

    async def _run():
        _rebuild_status["running"] = True
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, _build_kb)
            _rebuild_status["last"] = rag_state.get("built_at")
        finally:
            _rebuild_status["running"] = False

    background_tasks.add_task(_run)
    return {"status": "rebuilding", "message": "Knowledge base rebuild started. Check /api/health for completion."}


# ── Chat endpoint ──────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    top_k: int = 5
    model: str = "google/gemma-4-31b-it:free"


@app.post("/api/chat")
async def chat(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    if len(req.message) > 4000:
        raise HTTPException(status_code=400, detail="Message exceeds 4000 characters.")
    if not 1 <= req.top_k <= 20:
        raise HTTPException(status_code=400, detail="top_k must be between 1 and 20.")

    embedder: Embedder = rag_state["embedder"]
    store: VectorStore = rag_state["store"]
    client: OpenAI = rag_state["client"]

    loop = asyncio.get_event_loop()
    query_embedding = await loop.run_in_executor(None, embedder.embed_query, req.message)
    results = store.search(query_embedding, top_k=req.top_k)

    sources = [
        {"source": chunk.source, "text": chunk.text, "distance": round(dist, 4)}
        for chunk, dist in results
    ]

    context = "\n\n---\n\n".join(
        f"[Source: {chunk.source}]\n{chunk.text}" for chunk, _ in results
    )

    system_prompt = (
        "You are a knowledgeable and friendly AI assistant with access to a large knowledge base. "
        "Answer the user's question in a clear, well-structured way.\n\n"
        "Guidelines:\n"
        "- Use the CONTEXT passages below when they are relevant — they come from the user's indexed documents.\n"
        "- If the context covers the topic, weave that information naturally into your answer.\n"
        "- If the context doesn't fully cover the topic, also use your general knowledge.\n"
        "- Format responses with markdown: **bold** for key terms, bullet lists for multiple points, "
        "short paragraphs. Keep answers concise but complete.\n"
        "- For greetings or general conversation, respond naturally without forcing the context.\n"
        "- Only say you lack information if the question requires private/proprietary data "
        "that is genuinely absent from both the context and your training.\n\n"
        f"CONTEXT:\n{context}"
    )

    def event_stream():
        yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"
        try:
            stream = client.chat.completions.create(
                model=req.model,
                max_tokens=1024,
                stream=True,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": req.message},
                ],
            )
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield f"data: {json.dumps({'type': 'token', 'text': chunk.choices[0].delta.content})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'text': str(e)})}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
