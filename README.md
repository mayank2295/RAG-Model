# News & Jobs RAG Chatbot

A cloud-native Retrieval-Augmented Generation chatbot that fetches **today's
latest news** (NewsAPI.org) and **remote job openings** (Remotive), embeds them
into **Pinecone**, and answers your questions through an **OpenRouter** LLM with
real-time SSE streaming.

Everything runs in memory + Pinecone — there is **no local file storage**, so it
deploys cleanly on Render's free tier and survives restarts.

## How it works

1. **Ingest** — `news_fetcher` and `jobs_fetcher` pull fresh data, embed it with
   `sentence-transformers/all-MiniLM-L6-v2`, and upsert into Pinecone namespaces
   `news` and `jobs`.
2. **Schedule** — an APScheduler `BackgroundScheduler` re-ingests every 6 hours
   (plus one ingest at startup).
3. **Chat** — your question is embedded, matched against both namespaces, and the
   top results become context for `anthropic/claude-3-haiku` via OpenRouter. The
   answer streams back token-by-token over Server-Sent Events.

## Setup (local)

```bash
git clone https://github.com/mayank2295/RAG-Model.git
cd RAG-Model

cp .env.example .env        # then fill in your keys
pip install -r requirements.txt

uvicorn server:app --host 0.0.0.0 --port 10000
```

Open http://localhost:10000

### Environment variables

| Variable             | Description                                   |
|----------------------|-----------------------------------------------|
| `PINECONE_API_KEY`   | Pinecone API key                              |
| `PINECONE_INDEX`     | Pinecone index name (created automatically)   |
| `NEWSAPI_KEY`        | NewsAPI.org API key                           |
| `OPENROUTER_API_KEY` | OpenRouter API key                            |

## Deploy on Render

**Option A — Blueprint (one click):** this repo ships a `render.yaml`. In Render:
**New + → Blueprint**, connect the repo, and Render reads the build/start commands
automatically. You'll be prompted to fill the three secret env vars.

**Option B — manual Web Service:**

1. Push this repo to GitHub and connect it as a new **Web Service** on Render.
2. Add the four environment variables above under **Environment**.
3. **Build command:** `pip install -r requirements.txt`
4. **Start command:** `uvicorn server:app --host 0.0.0.0 --port $PORT`
5. Deploy. The first boot runs an initial ingest, then it self-refreshes every
   6 hours.

> **Free-tier note:** the embedding model (PyTorch + MiniLM) needs ~400–500 MB
> RAM. Render's free instance has 512 MB, which is tight — if the service OOMs
> on boot, upgrade to the **Starter** plan.

## API endpoints

| Method | Path           | Description                                            |
|--------|----------------|--------------------------------------------------------|
| `GET`  | `/`            | Chat UI                                                |
| `POST` | `/api/chat`    | SSE streaming answer. Body: `{"message": str, "top_k": int}` |
| `POST` | `/api/ingest`  | Manually trigger a news + jobs ingest                  |
| `GET`  | `/api/status`  | Last ingest time + vector counts per namespace         |

## Data sources

- **News:** [NewsAPI.org](https://newsapi.org) — categories: technology, business, science
- **Jobs:** [Remotive](https://remotive.com/api/remote-jobs) — categories: software-dev, data, devops (no key required)
