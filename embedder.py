"""
Embedding module — sentence-transformers/all-MiniLM-L6-v2.

Loads the model once (singleton) at first use and reuses it for every
embedding call. Produces 384-dimensional vectors suitable for Pinecone.

Public API:
    embed_text(text)   -> list[float]
    embed_batch(texts) -> list[list[float]]
"""

import logging
import threading
import time
from typing import List

from sentence_transformers import SentenceTransformer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("embedder")

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
# all-MiniLM-L6-v2 has a 256 word-piece limit; we cap characters generously
# below the 512-token ceiling requested. SentenceTransformer truncates
# internally, but we also hard-cap to keep memory predictable.
MAX_CHARS = 2000  # ~512 tokens worst case

_model: SentenceTransformer | None = None
_model_lock = threading.Lock()


def _get_model() -> SentenceTransformer:
    """Return the singleton SentenceTransformer, loading it once if needed."""
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                logger.info("Loading embedding model '%s' ...", MODEL_NAME)
                t0 = time.time()
                _model = SentenceTransformer(MODEL_NAME)
                # Enforce the 512-token cap requested in the spec.
                _model.max_seq_length = 512
                logger.info(
                    "Embedding model ready in %.1fs (dim=%d, max_seq_len=%d)",
                    time.time() - t0,
                    _model.get_sentence_embedding_dimension(),
                    _model.max_seq_length,
                )
    return _model


def _truncate(text: str) -> str:
    """Trim text to a safe character length before embedding."""
    text = (text or "").strip()
    if len(text) > MAX_CHARS:
        return text[:MAX_CHARS]
    return text


def embed_text(text: str) -> List[float]:
    """
    Embed a single string into a 384-dimensional vector.

    Args:
        text: Raw input text. Truncated to a safe length (~512 tokens).

    Returns:
        A list of floats (the embedding). Empty input still returns a valid
        zero-meaning vector for the empty string so callers never crash.
    """
    model = _get_model()
    vector = model.encode(
        _truncate(text),
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    return vector.astype("float32").tolist()


def embed_batch(texts: List[str]) -> List[List[float]]:
    """
    Embed a list of strings into a list of 384-dimensional vectors.

    Args:
        texts: List of raw input strings. Each is truncated independently.

    Returns:
        A list of embedding vectors, one per input string, in the same order.
    """
    if not texts:
        return []
    model = _get_model()
    cleaned = [_truncate(t) for t in texts]
    vectors = model.encode(
        cleaned,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,
        batch_size=32,
    )
    logger.info("Embedded batch of %d texts", len(cleaned))
    return [v.astype("float32").tolist() for v in vectors]


def warm_up() -> None:
    """Pre-load the model at startup so the first request isn't slow."""
    _get_model()
