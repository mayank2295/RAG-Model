"""
Embedding module — fastembed (ONNX) with BAAI/bge-small-en-v1.5.

Uses fastembed instead of sentence-transformers/PyTorch to keep the memory
footprint small enough for a 512 MB cloud instance. The model produces
384-dimensional vectors (same dimension as all-MiniLM-L6-v2), so the existing
Pinecone index dimension is unchanged.

Loads the model once (singleton) at first use.

Public API:
    embed_text(text)   -> list[float]
    embed_batch(texts) -> list[list[float]]
"""

import logging
import threading
import time
from typing import List

from fastembed import TextEmbedding

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("embedder")

MODEL_NAME = "BAAI/bge-small-en-v1.5"  # 384-dim, ONNX, low memory
EMBEDDING_DIM = 384
MAX_CHARS = 2000  # ~512 tokens worst case

_model: TextEmbedding | None = None
_model_lock = threading.Lock()


def _get_model() -> TextEmbedding:
    """Return the singleton TextEmbedding model, loading it once if needed."""
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                logger.info("Loading embedding model '%s' (fastembed/ONNX) ...", MODEL_NAME)
                t0 = time.time()
                _model = TextEmbedding(model_name=MODEL_NAME)
                logger.info(
                    "Embedding model ready in %.1fs (dim=%d)",
                    time.time() - t0, EMBEDDING_DIM,
                )
    return _model


def _truncate(text: str) -> str:
    """Trim text to a safe character length before embedding."""
    text = (text or "").strip()
    if len(text) > MAX_CHARS:
        return text[:MAX_CHARS]
    return text or " "  # fastembed needs non-empty input


def embed_text(text: str) -> List[float]:
    """
    Embed a single string into a 384-dimensional vector.

    Args:
        text: Raw input text. Truncated to a safe length (~512 tokens).

    Returns:
        A list of floats (the embedding).
    """
    model = _get_model()
    vector = next(iter(model.embed([_truncate(text)])))
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
    vectors = [v.astype("float32").tolist() for v in model.embed(cleaned)]
    logger.info("Embedded batch of %d texts", len(cleaned))
    return vectors


def warm_up() -> None:
    """Pre-load the model so the first request isn't slow."""
    _get_model()
