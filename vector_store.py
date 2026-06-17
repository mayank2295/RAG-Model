"""
Step 3 of RAG: Store and search embeddings with FAISS.

FAISS (Facebook AI Similarity Search) is a library for efficiently finding
the most similar vectors in a large collection. When you ask a question,
we embed it and then ask FAISS: "which of the stored document embeddings
are closest to this query embedding?"

'Closest' here means cosine similarity or L2 distance — vectors pointing in
the same direction in high-dimensional space represent similar meanings.
"""

import numpy as np
import faiss
from typing import List, Tuple
from document_loader import Chunk


class VectorStore:
    def __init__(self, embedding_dim: int):
        """
        Create a flat (exact, brute-force) FAISS index.

        For production you'd use an approximate index (e.g. IndexIVFFlat)
        for speed on millions of vectors, but flat search is fine and fully
        accurate for a small knowledge base.
        """
        self.index = faiss.IndexFlatL2(embedding_dim)
        self.chunks: List[Chunk] = []  # keep chunks in sync with the index
        self.embedding_dim = embedding_dim
        print(f"[VectorStore] Created FAISS index with dim={embedding_dim}")

    def add(self, chunks: List[Chunk], embeddings: np.ndarray):
        """
        Insert chunks and their embeddings into the store.

        FAISS only stores the vectors; we keep the original text in
        self.chunks so we can return it alongside search results.
        """
        assert len(chunks) == len(embeddings), "Each chunk must have exactly one embedding"
        self.index.add(embeddings)
        self.chunks.extend(chunks)
        print(f"[VectorStore] Indexed {len(chunks)} chunks. Total: {self.index.ntotal}")

    def search(self, query_embedding: np.ndarray, top_k: int = 3) -> List[Tuple[Chunk, float]]:
        """
        Find the top_k chunks most similar to the query embedding.

        Returns a list of (Chunk, distance) tuples sorted by similarity.
        Lower L2 distance = more similar.
        """
        distances, indices = self.index.search(query_embedding, top_k)

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx != -1:  # FAISS returns -1 when fewer results exist than top_k
                results.append((self.chunks[idx], float(dist)))

        return results
