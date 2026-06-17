# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the web UI (opens at http://localhost:8000)
uvicorn server:app --reload

# Run the CLI demo instead
python main.py

# Run a single query non-interactively (for testing)
python -c "from rag_pipeline import RAGPipeline; r = RAGPipeline(); print(r.query('What is RAG?')['answer'])"
```

Set `ANTHROPIC_API_KEY` in the environment before running (see `.env.example`).

## Architecture

This is a minimal RAG (Retrieval-Augmented Generation) implementation with a strict one-responsibility-per-file structure:

```
document_loader.py  →  embedder.py  →  vector_store.py
                                              ↓
                               rag_pipeline.py (orchestrates all three)
                                    ↙              ↘
                               main.py (CLI)   server.py (FastAPI web UI)
                                                      ↓
                                              static/index.html
```

**Web UI (`server.py` + `static/index.html`):** FastAPI serves `GET /` → `static/index.html` and `POST /api/chat` → SSE stream. The stream emits three event types in order: `sources` (JSON array of retrieved chunks), `token` (streamed LLM text), `done`. The frontend handles all three to render sources immediately and stream text word-by-word. The RAG knowledge base is built once in the FastAPI `lifespan` event and stored in `rag_state` dict for the lifetime of the process.

**Data flow at startup:** `load_documents()` reads `documents/*.txt`, splits text into overlapping `Chunk` objects → `Embedder.embed()` converts chunk texts to float32 numpy arrays via `sentence-transformers` → `VectorStore.add()` inserts those arrays into a FAISS `IndexFlatL2`.

**Data flow per query:** `Embedder.embed_query()` encodes the user question → `VectorStore.search()` returns top-K `(Chunk, distance)` tuples → `RAGPipeline.generate()` builds a system prompt containing the chunk texts and calls `anthropic.Anthropic().messages.create()`.

## Key design decisions

- **FAISS `IndexFlatL2`** (brute-force exact search) is used deliberately for correctness and simplicity; switch to `IndexIVFFlat` if scaling beyond ~100K chunks.
- **`self.chunks` list in `VectorStore`** stays in sync with the FAISS index — FAISS stores only vectors, so we need the parallel list to recover the original text after search.
- **`float32` cast in `Embedder.embed()`** is required by FAISS; sentence-transformers returns float32 by default but the explicit cast prevents breakage if the model changes.
- **Model:** `claude-haiku-4-5-20251001` is the default for speed and cost; change the `model` param in `RAGPipeline.__init__()` to use Sonnet or Opus.
- Adding documents: drop `.txt` files into `documents/` and restart — no other changes needed.
