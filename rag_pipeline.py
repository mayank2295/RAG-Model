"""
Step 4 of RAG: The full pipeline — Retrieve then Generate.

This is where RAG gets its name:
  R = Retrieval  → find relevant document chunks for the user's query
  A = Augmented  → combine those chunks with the query into a prompt
  G = Generation → send the augmented prompt to an LLM for a final answer

Without retrieval, an LLM can only answer from its training data (which may
be outdated or not contain your specific documents). With RAG, the LLM
"reads" your documents at query time and can answer with fresh, specific info.
"""

import os
from openai import OpenAI
from typing import List

from document_loader import load_documents, Chunk
from embedder import Embedder
from vector_store import VectorStore


class RAGPipeline:
    def __init__(
        self,
        documents_dir: str = "documents",
        chunk_size: int = 300,
        overlap: int = 50,
        top_k: int = 3,
        model: str = "google/gemma-4-31b-it:free",
    ):
        self.top_k = top_k
        self.model = model
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ.get("OPENROUTER_API_KEY"),
        )

        # --- Build the knowledge base ---
        print("\n=== Building Knowledge Base ===")

        # 1. Load & chunk documents
        self.chunks: List[Chunk] = load_documents(documents_dir, chunk_size=chunk_size, overlap=overlap)

        # 2. Embed all chunks
        self.embedder = Embedder()
        chunk_texts = [c.text for c in self.chunks]
        chunk_embeddings = self.embedder.embed(chunk_texts)

        # 3. Store in FAISS
        embedding_dim = chunk_embeddings.shape[1]
        self.store = VectorStore(embedding_dim=embedding_dim)
        self.store.add(self.chunks, chunk_embeddings)

        print("=== Knowledge Base Ready ===\n")

    def retrieve(self, query: str):
        """Embed the query and find the most relevant chunks."""
        query_embedding = self.embedder.embed_query(query)
        results = self.store.search(query_embedding, top_k=self.top_k)
        return results

    def generate(self, query: str, context_chunks: list) -> str:
        """
        Build a prompt with the retrieved context and call the LLM.

        The system prompt instructs the model to answer ONLY from the provided
        context. This is important — it stops the LLM from hallucinating
        information that isn't in your documents.
        """
        context = "\n\n---\n\n".join(
            f"[Source: {chunk.source}]\n{chunk.text}" for chunk, _ in context_chunks
        )

        system_prompt = (
            "You are a helpful assistant. Answer the user's question using ONLY "
            "the context provided below. If the answer cannot be found in the "
            "context, say 'I don't have enough information in my knowledge base "
            "to answer that.' Do not make up information.\n\n"
            f"CONTEXT:\n{context}"
        )

        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=512,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query},
            ],
        )

        return response.choices[0].message.content or ""

    def query(self, user_question: str) -> dict:
        """
        End-to-end RAG: retrieve relevant chunks, then generate an answer.

        Returns a dict with:
          - answer: the LLM's response
          - sources: which document chunks were used
        """
        print(f"\n[RAG] Query: '{user_question}'")

        # Retrieve
        print(f"[RAG] Retrieving top {self.top_k} relevant chunks...")
        results = self.retrieve(user_question)

        for i, (chunk, dist) in enumerate(results):
            print(f"  #{i+1} distance={dist:.4f} | source={chunk.source} | '{chunk.text[:60]}...'")

        # Generate
        print("[RAG] Generating answer with the selected LLM...")
        answer = self.generate(user_question, results)

        return {
            "question": user_question,
            "answer": answer,
            "sources": [{"source": c.source, "text": c.text, "distance": d} for c, d in results],
        }
