"""
Step 1 of RAG: Load documents and split them into chunks.

Supports:
  .txt   — plain text
  .csv   — extracts the largest text column automatically
  .json  — flat objects; extracts longest string value
  .jsonl — one JSON object per line

Walks subdirectories recursively so documents can be organized in
category folders (documents/wikipedia/, documents/news/, etc.).
"""

import os
import csv
import json
from pathlib import Path
from typing import List


class Chunk:
    """A piece of text with metadata about where it came from."""

    def __init__(self, text: str, source: str, chunk_id: int):
        self.text = text
        self.source = source
        self.chunk_id = chunk_id

    def __repr__(self):
        return f"Chunk(id={self.chunk_id}, source='{self.source}', text='{self.text[:60]}...')"


# ── File readers ──────────────────────────────────────────────────────────────

def _read_txt(filepath: Path) -> str:
    return filepath.read_text(encoding="utf-8", errors="ignore")


def _read_csv(filepath: Path) -> str:
    """Return all text-heavy columns concatenated, one row per paragraph."""
    try:
        with open(filepath, encoding="utf-8", errors="ignore", newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        if not rows:
            return ""
        # Find columns whose average value length > 40 chars (likely text columns)
        text_cols = [
            col for col in rows[0]
            if sum(len(str(r.get(col, ""))) for r in rows[:20]) / min(20, len(rows)) > 40
        ]
        if not text_cols:
            text_cols = list(rows[0].keys())
        parts = []
        for row in rows:
            fragment = " | ".join(str(row[c]).strip() for c in text_cols if row.get(c))
            if fragment:
                parts.append(fragment)
        return "\n\n".join(parts)
    except Exception:
        return ""


def _read_json(filepath: Path) -> str:
    """Read a JSON file (object or array) and extract all string values."""
    try:
        raw = filepath.read_text(encoding="utf-8", errors="ignore")
        data = json.loads(raw)
        return _extract_strings(data)
    except Exception:
        return ""


def _read_jsonl(filepath: Path) -> str:
    """Read a JSONL file (one JSON object per line)."""
    parts = []
    try:
        for line in filepath.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                parts.append(_extract_strings(obj))
            except json.JSONDecodeError:
                continue
    except Exception:
        pass
    return "\n\n".join(p for p in parts if p)


def _extract_strings(obj) -> str:
    """Recursively pull all string values from a JSON object/array."""
    if isinstance(obj, str):
        return obj
    if isinstance(obj, dict):
        return " ".join(_extract_strings(v) for v in obj.values())
    if isinstance(obj, list):
        return " ".join(_extract_strings(item) for item in obj)
    return ""


_READERS = {
    ".txt":   _read_txt,
    ".csv":   _read_csv,
    ".json":  _read_json,
    ".jsonl": _read_jsonl,
}


# ── Chunking ──────────────────────────────────────────────────────────────────

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 80) -> List[str]:
    """
    Split text into overlapping chunks of roughly `chunk_size` characters.
    Tries to break on sentence boundaries ('. ') to keep meaning intact.
    """
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        if end < len(text):
            # Try to find a clean sentence break within the last 100 chars
            boundary = text.rfind(". ", start, end)
            if boundary != -1 and boundary > start + chunk_size // 2:
                end = boundary + 2
        fragment = text[start:end].strip()
        if fragment:
            chunks.append(fragment)
        start = end - overlap
    return chunks


# ── Main loader ───────────────────────────────────────────────────────────────

def load_documents(documents_dir: str, chunk_size: int = 500, overlap: int = 80) -> List[Chunk]:
    """
    Recursively load all supported files from documents_dir and return Chunks.

    Walks subdirectories so you can organize documents by category:
        documents/wikipedia/
        documents/news/
        documents/science/arxiv/
    """
    all_chunks: List[Chunk] = []
    chunk_id = 0
    doc_dir = Path(documents_dir)

    if not doc_dir.exists():
        print(f"[Loader] Warning: '{documents_dir}' not found. Run: python ingest.py")
        return []

    # Collect all supported files recursively
    files = sorted(
        p for p in doc_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in _READERS
    )

    if not files:
        print(f"[Loader] No supported files in '{documents_dir}'. Run: python ingest.py")
        return []

    file_count = 0
    for filepath in files:
        suffix = filepath.suffix.lower()
        reader = _READERS[suffix]
        text = reader(filepath)
        if not text or len(text.strip()) < 50:
            continue

        # Use relative path as source label  (e.g. "wikipedia/0001_Banana.txt")
        try:
            rel = filepath.relative_to(doc_dir)
        except ValueError:
            rel = filepath.name
        source = str(rel).replace("\\", "/")

        raw_chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)
        for raw in raw_chunks:
            if raw:
                all_chunks.append(Chunk(text=raw, source=source, chunk_id=chunk_id))
                chunk_id += 1
        file_count += 1

    print(
        f"[Loader] {file_count} files → {len(all_chunks):,} chunks  "
        f"(dir: '{documents_dir}')"
    )
    return all_chunks
