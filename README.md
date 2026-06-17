# Simple RAG Model

A from-scratch implementation of **Retrieval-Augmented Generation (RAG)** designed to be read and understood, not just run. Every file is heavily commented to explain the *why*, not just the *what*.

---

## What is RAG?

Imagine you ask a question to a very smart person who has only read general books (an LLM). They'll give you a reasonable answer, but they might not know the specific details in *your* documents.

RAG solves this by first **searching your documents** for relevant information, then **handing that information** to the LLM so it can answer with grounded, specific facts.

```
User Question
     │
     ▼
┌─────────────────────────────────────────────────────────┐
│                     RAG Pipeline                        │
│                                                         │
│  ┌──────────────┐    ┌──────────────┐   ┌───────────┐  │
│  │   Embedder   │───▶│ Vector Store │──▶│ Retrieved │  │
│  │ (encodes the │    │    (FAISS)   │   │  Chunks   │  │
│  │   question)  │    │ (finds most  │   │           │  │
│  └──────────────┘    │  similar     │   └─────┬─────┘  │
│                      │  chunks)     │         │        │
│                      └──────────────┘         │        │
│                                               ▼        │
│                                    ┌──────────────────┐ │
│                                    │   Claude LLM     │ │
│                                    │ (reads context + │ │
│                                    │ writes answer)   │ │
│                                    └──────────────────┘ │
└─────────────────────────────────────────────────────────┘
     │
     ▼
  Answer (grounded in YOUR documents)
```

---

## How It Works — Step by Step

### Phase 1: Indexing (happens once at startup)

```
Documents (text files)
       │
       ▼
  document_loader.py  ──▶  Splits text into overlapping chunks
       │
       ▼
  embedder.py         ──▶  Converts each chunk into a 384-dim vector
       │
       ▼
  vector_store.py     ──▶  Stores all vectors in a FAISS index
```

**Why chunks?** LLMs have a limited context window. Instead of passing an entire document, we pass only the most relevant pieces.

**Why overlap?** If a sentence spans two chunks, overlap ensures it's captured in at least one of them.

**Why vectors?** Vectors let us do *semantic search* — finding text that means the same thing even with different words. "automobile" and "car" have similar vectors.

### Phase 2: Retrieval + Generation (happens per query)

```
User question: "What is RAG?"
       │
       ▼
  embedder.py     ──▶  Encodes question into a vector
       │
       ▼
  vector_store.py ──▶  Finds top-3 closest chunk vectors (via L2 distance)
       │
       ▼
  rag_pipeline.py ──▶  Builds a prompt:
                         System: "Answer from this context only: [chunks]"
                         User:   "What is RAG?"
       │
       ▼
  Claude API      ──▶  Generates a grounded answer
       │
       ▼
  Answer + source citations
```

---

## Project Structure

```
.
├── document_loader.py   # Load .txt files and split into chunks
├── embedder.py          # sentence-transformers: text → vectors
├── vector_store.py      # FAISS: store and search vectors
├── rag_pipeline.py      # Orchestrates retrieve → generate (CLI use)
├── server.py            # FastAPI web server with streaming SSE endpoint
├── main.py              # Interactive CLI demo
├── static/
│   └── index.html       # Chat UI (dark-themed, streaming, source citations)
├── requirements.txt
├── .env.example
└── documents/           # Your knowledge base (add .txt files here)
    ├── ai_basics.txt
    ├── rag_explained.txt
    └── llm_concepts.txt
```

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

> The first run will download the `all-MiniLM-L6-v2` embedding model (~90 MB). It's cached after that.

### 2. Set your API key

```bash
# Windows
set ANTHROPIC_API_KEY=your_key_here

# macOS/Linux
export ANTHROPIC_API_KEY=your_key_here
```

Get a free key at [console.anthropic.com](https://console.anthropic.com).

### 3a. Run the web UI (recommended)

```bash
uvicorn server:app --reload
```

Then open **http://localhost:8000** in your browser. You'll get a full chatbot interface with:
- Streaming answers (text appears word-by-word)
- Collapsible source citations per answer
- Model switcher (Haiku / Sonnet)
- Adjustable number of retrieved sources

### 3b. Or run the CLI

```bash
python main.py
```

### Example session

```
=== Building Knowledge Base ===
[Loader] Loaded 42 chunks from 'documents'
[Embedder] Loading model 'all-MiniLM-L6-v2'...
[VectorStore] Indexed 42 chunks. Total: 42
=== Knowledge Base Ready ===

RAG is ready! Type your question (or 'quit' to exit).

You: What is the difference between supervised and unsupervised learning?

[RAG] Retrieving top 3 relevant chunks...
  #1 distance=0.2341 | source=ai_basics.txt | 'Supervised learning is a type of machine learning where...'
  #2 distance=0.3102 | source=ai_basics.txt | 'Unsupervised learning involves training a model on data...'
  #3 distance=0.4891 | source=llm_concepts.txt | 'Fine-tuning is the process of taking a pre-trained...'

[RAG] Generating answer with Claude...

Answer: Supervised learning trains a model on labeled data (input-output pairs), 
teaching it to map inputs to known outputs — used in tasks like spam detection. 
Unsupervised learning trains on unlabeled data, letting the model discover 
patterns on its own — used in clustering and dimensionality reduction.

Sources used:
  [1] ai_basics.txt (distance=0.2341)
  [2] ai_basics.txt (distance=0.3102)
  [3] llm_concepts.txt (distance=0.4891)
```

---

## Add Your Own Documents

Just drop `.txt` files into the `documents/` folder and restart. The pipeline indexes everything automatically.

```
documents/
├── my_company_handbook.txt
├── product_specs.txt
└── faq.txt
```

---

## Key Concepts Glossary

| Term | What it means |
|------|--------------|
| **Embedding** | A list of numbers representing the *meaning* of text |
| **Vector store** | A database optimized for searching by vector similarity |
| **Chunk** | A small piece of a document (300 chars here) |
| **Overlap** | Shared text between adjacent chunks to avoid cutting ideas in half |
| **L2 distance** | How far apart two vectors are; lower = more similar |
| **Top-K retrieval** | Returning the K closest chunks to the query |
| **Context window** | The max text an LLM can read at once |
| **Hallucination** | When an LLM makes up facts; RAG reduces this |
| **System prompt** | Instructions that tell the LLM how to behave |

---

## Tuning Tips

| Parameter | Default | Effect |
|-----------|---------|--------|
| `chunk_size` | 300 chars | Smaller = more precise retrieval, less context per chunk |
| `overlap` | 50 chars | More overlap = fewer boundary losses, more storage |
| `top_k` | 3 | More retrieved chunks = richer context, longer prompt |
| `model` | `claude-haiku-4-5` | Swap to `claude-sonnet-4-6` for better answers |
