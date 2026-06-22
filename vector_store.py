"""
Vector store — Pinecone v3+ wrapper.

Wraps the Pinecone serverless index with three helpers used across the app:
    upsert_vectors(vectors, namespace)
    query_vectors(query_vector, namespace, top_k)
    query_all_namespaces(query_vector, top_k)

Config is read entirely from environment variables:
    PINECONE_API_KEY   — Pinecone API key
    PINECONE_INDEX     — name of the index to use/create

The index is created on first use if it does not exist (384 dims, cosine,
AWS us-east-1 serverless — the free-tier default).
"""

import logging
import os
import threading
import time
from typing import Dict, List

from pinecone import Pinecone, ServerlessSpec

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("vector_store")

EMBEDDING_DIM = 384  # all-MiniLM-L6-v2
NAMESPACES = ("news", "jobs")

_pc: Pinecone | None = None
_index = None
_init_lock = threading.Lock()


def _list_index_names(pc: Pinecone) -> set:
    """Return the set of existing index names, tolerant of SDK return shapes."""
    result = pc.list_indexes()
    # Pinecone v3+ exposes .names(); fall back to iterating objects/dicts.
    names_fn = getattr(result, "names", None)
    if callable(names_fn):
        return set(names_fn())
    out = set()
    for item in result:
        name = getattr(item, "name", None)
        if name is None and isinstance(item, dict):
            name = item.get("name")
        if name:
            out.add(name)
    return out


def _to_dict(obj):
    """Best-effort conversion of a Pinecone response object to a dict."""
    if isinstance(obj, dict):
        return obj
    to_dict = getattr(obj, "to_dict", None)
    if callable(to_dict):
        return to_dict()
    return obj


def _get_index():
    """Return the singleton Pinecone index handle, creating it if missing."""
    global _pc, _index
    if _index is not None:
        return _index

    with _init_lock:
        if _index is not None:
            return _index

        api_key = os.environ.get("PINECONE_API_KEY")
        index_name = os.environ.get("PINECONE_INDEX")
        if not api_key:
            raise RuntimeError("PINECONE_API_KEY environment variable is not set.")
        if not index_name:
            raise RuntimeError("PINECONE_INDEX environment variable is not set.")

        logger.info("Connecting to Pinecone ...")
        _pc = Pinecone(api_key=api_key)

        existing = _list_index_names(_pc)
        if index_name not in existing:
            logger.info("Index '%s' not found — creating it.", index_name)
            _pc.create_index(
                name=index_name,
                dimension=EMBEDDING_DIM,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1"),
            )
            # Wait for the index to become ready.
            for _ in range(30):
                desc = _pc.describe_index(index_name)
                status = getattr(desc, "status", None)
                ready = getattr(status, "ready", None) if status is not None else None
                if ready is None and isinstance(status, dict):
                    ready = status.get("ready")
                if ready:
                    break
                time.sleep(2)
            logger.info("Index '%s' created and ready.", index_name)
        else:
            logger.info("Using existing Pinecone index '%s'.", index_name)

        _index = _pc.Index(index_name)
        return _index


def upsert_vectors(vectors: List[Dict], namespace: str) -> int:
    """
    Upsert a batch of vectors into a namespace.

    Args:
        vectors: List of dicts, each with keys "id" (str), "values"
            (list[float]) and "metadata" (dict).
        namespace: Target namespace, e.g. "news" or "jobs".

    Returns:
        The number of vectors successfully upserted.
    """
    if not vectors:
        logger.info("upsert_vectors: nothing to upsert for namespace '%s'.", namespace)
        return 0

    index = _get_index()
    total = 0
    # Pinecone recommends batches of <=100 for serverless.
    for start in range(0, len(vectors), 100):
        batch = vectors[start:start + 100]
        try:
            index.upsert(vectors=batch, namespace=namespace)
            total += len(batch)
        except Exception:
            logger.exception(
                "Failed to upsert batch [%d:%d] into namespace '%s'.",
                start, start + len(batch), namespace,
            )
    logger.info("Upserted %d vectors into namespace '%s'.", total, namespace)
    return total


def query_vectors(query_vector: List[float], namespace: str, top_k: int = 5) -> List[Dict]:
    """
    Query a single namespace for the most similar vectors.

    Args:
        query_vector: The query embedding.
        namespace: Namespace to search, e.g. "news" or "jobs".
        top_k: Number of matches to return.

    Returns:
        A list of match dicts: {"id", "score", "namespace", "metadata"}.
    """
    index = _get_index()
    try:
        res = index.query(
            vector=query_vector,
            namespace=namespace,
            top_k=top_k,
            include_metadata=True,
        )
    except Exception:
        logger.exception("Query failed for namespace '%s'.", namespace)
        return []

    raw_matches = _to_dict(res).get("matches", []) or []
    matches = []
    for m in raw_matches:
        md = _to_dict(m)
        matches.append({
            "id": md.get("id"),
            "score": md.get("score"),
            "namespace": namespace,
            "metadata": md.get("metadata", {}) or {},
        })
    logger.info("Query namespace '%s' → %d matches.", namespace, len(matches))
    return matches


def query_all_namespaces(query_vector: List[float], top_k: int = 5) -> List[Dict]:
    """
    Query every known namespace and merge the results.

    Args:
        query_vector: The query embedding.
        top_k: Number of matches to take from EACH namespace.

    Returns:
        A merged list of match dicts sorted by descending score.
    """
    all_matches: List[Dict] = []
    for ns in NAMESPACES:
        all_matches.extend(query_vectors(query_vector, namespace=ns, top_k=top_k))
    all_matches.sort(key=lambda m: m.get("score") or 0.0, reverse=True)
    return all_matches


def namespace_counts() -> Dict[str, int]:
    """
    Return the vector count per namespace from index stats.

    Returns:
        Dict mapping namespace name to its vector count (0 if absent).
    """
    index = _get_index()
    try:
        stats = _to_dict(index.describe_index_stats())
        ns_stats = stats.get("namespaces", {}) or {}
        return {
            ns: _to_dict(ns_stats.get(ns, {})).get("vector_count", 0)
            for ns in NAMESPACES
        }
    except Exception:
        logger.exception("Failed to fetch namespace stats.")
        return {ns: 0 for ns in NAMESPACES}
