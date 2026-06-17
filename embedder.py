"""
Step 2 of RAG: Turn text into vectors (embeddings).

An embedding is a list of numbers (a vector) that captures the *meaning* of
a sentence. Sentences with similar meanings end up with similar vectors.
This is what makes semantic search possible — we don't look for exact word
matches, we look for meaning matches.

We use sentence-transformers (runs locally, no API key needed) with the
'all-MiniLM-L6-v2' model, which produces 384-dimensional vectors and is
fast enough to run on a laptop CPU.
"""

import numpy as np
from typing import List
from sentence_transformers import SentenceTransformer


class Embedder:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        print(f"[Embedder] Loading model '{model_name}' (downloads once, then cached)...")
        self.model = SentenceTransformer(model_name)
        dim = getattr(self.model, 'get_embedding_dimension', self.model.get_sentence_embedding_dimension)()
        print(f"[Embedder] Model ready. Embedding dimension: {dim}")

    def embed(self, texts: List[str]) -> np.ndarray:
        """
        Convert a list of strings into a 2-D numpy array of shape (N, D)
        where N = number of texts and D = embedding dimension (384).

        Both document chunks and user queries go through this same function —
        that's the key: they land in the same vector space, so we can compare them.
        """
        vectors = self.model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
        return vectors.astype("float32")  # FAISS expects float32

    def embed_query(self, query: str) -> np.ndarray:
        """Embed a single query string. Returns shape (1, D)."""
        return self.embed([query])
