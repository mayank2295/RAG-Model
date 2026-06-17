"""
Dataset ingestion for RAG pipeline.

Downloads real-world datasets and saves them to documents/.
Supports Kaggle (primary) and HuggingFace (no-auth fallback).

Usage:
    python ingest.py               # auto mode
    python ingest.py --source hf   # HuggingFace only (no account needed)
    python ingest.py --source kaggle
    python ingest.py --max 300     # limit articles per dataset
    python ingest.py --clear       # wipe documents/ before ingesting
    python ingest.py --list        # list available datasets

Kaggle setup (one-time):
    1. Sign in at https://www.kaggle.com -> Settings -> Create New Token
    2. Download kaggle.json
    3. Place it at C:\\Users\\<you>\\.kaggle\\kaggle.json
"""

import os
import sys
import json
import csv
import argparse
import textwrap
import shutil
from pathlib import Path

DOCS_DIR = Path("documents")
TEMP_DIR = Path(".kaggle_tmp")


def sanitize(name, maxlen=60):
    return "".join(c if c.isalnum() or c in " _-" else "_" for c in name)[:maxlen].strip()


def save_txt(directory, index, title, body, max_chars=8000):
    directory.mkdir(parents=True, exist_ok=True)
    fname = f"{index:05d}_{sanitize(title)}.txt"
    (directory / fname).write_text(body[:max_chars], encoding="utf-8", errors="ignore")


def check_kaggle():
    creds = Path.home() / ".kaggle" / "kaggle.json"
    return creds.exists()


def print_section(title):
    print("\n" + "-" * 60)
    print("  " + title)
    print("-" * 60)


# ── HuggingFace datasets ──────────────────────────────────────────

def ingest_wikipedia(max_articles=500):
    """Wikipedia Simple English articles."""
    print_section(f"Wikipedia Simple English ({max_articles} articles)")
    try:
        from datasets import load_dataset
        try:
            ds = load_dataset("wikimedia/wikipedia", "20231101.simple",
                              split=f"train[:{max_articles}]")
        except Exception:
            ds = load_dataset("wikipedia", "20220301.simple",
                              split=f"train[:{max_articles}]")
        out = DOCS_DIR / "wikipedia"
        count = 0
        for i, art in enumerate(ds):
            text = art.get("text", "").strip()
            if len(text) < 100:
                continue
            body = "# " + art["title"] + "\n\n" + text
            save_txt(out, i, art["title"], body)
            count += 1
        print(f"  [OK] Saved {count} Wikipedia articles -> {out}")
        return count
    except Exception as e:
        print(f"  [FAIL] Wikipedia: {e}")
        return 0


def ingest_ag_news(max_articles=500):
    """AG News — world, sports, business, science/tech."""
    print_section(f"AG News ({max_articles} articles)")
    try:
        from datasets import load_dataset
        labels = ["World", "Sports", "Business", "Science_Tech"]
        ds = load_dataset("ag_news", split=f"train[:{max_articles}]")
        out = DOCS_DIR / "news"
        count = 0
        for i, item in enumerate(ds):
            label = labels[item["label"]]
            body = f"Category: {label}\n\n{item['text']}"
            save_txt(out, i, f"{label}_{i}", body)
            count += 1
        print(f"  [OK] Saved {count} news articles -> {out}")
        return count
    except Exception as e:
        print(f"  [FAIL] AG News: {e}")
        return 0


def ingest_arxiv_hf(max_papers=300):
    """ArXiv paper abstracts via HuggingFace."""
    print_section(f"ArXiv Abstracts ({max_papers} papers)")
    try:
        from datasets import load_dataset
        ds = load_dataset("ccdv/arxiv-summarization",
                          split=f"train[:{max_papers}]")
        out = DOCS_DIR / "science" / "arxiv"
        count = 0
        for i, paper in enumerate(ds):
            abstract = paper.get("abstract", "").strip()
            article = paper.get("article", "").strip()
            if not abstract:
                continue
            if article:
                body = f"Abstract:\n{abstract}\n\nFull Text:\n{article[:3000]}"
            else:
                body = f"Abstract:\n{abstract}"
            save_txt(out, i, f"arxiv_{i}", body)
            count += 1
        print(f"  [OK] Saved {count} ArXiv papers -> {out}")
        return count
    except Exception as e:
        print(f"  [FAIL] ArXiv (HF): {e}")
        return 0


def ingest_squad_passages(max_passages=300):
    """SQuAD reading comprehension passages."""
    print_section(f"SQuAD Passages ({max_passages} unique passages)")
    try:
        from datasets import load_dataset
        ds = load_dataset("squad", split="train[:5000]")
        out = DOCS_DIR / "qa_passages"
        seen = set()
        passages = []
        for item in ds:
            ctx = item["context"].strip()
            if ctx not in seen and len(ctx) > 100:
                seen.add(ctx)
                passages.append({"title": item["title"], "context": ctx})
            if len(passages) >= max_passages:
                break
        count = 0
        for i, p in enumerate(passages):
            body = "# " + p["title"] + "\n\n" + p["context"]
            save_txt(out, i, p["title"], body)
            count += 1
        print(f"  [OK] Saved {count} passages -> {out}")
        return count
    except Exception as e:
        print(f"  [FAIL] SQuAD: {e}")
        return 0


def ingest_medical_hf(max_items=200):
    """Medical Q&A dataset."""
    print_section(f"Medical Q&A ({max_items} entries)")
    try:
        from datasets import load_dataset
        ds = load_dataset("medalpaca/medical_meadow_medqa",
                          split=f"train[:{max_items}]")
        out = DOCS_DIR / "medical"
        count = 0
        for i, item in enumerate(ds):
            instruction = item.get("instruction", "")
            output = item.get("output", "")
            if not instruction or not output:
                continue
            body = f"Question: {instruction}\n\nAnswer: {output}"
            save_txt(out, i, f"medical_{i}", body)
            count += 1
        print(f"  [OK] Saved {count} medical Q&A entries -> {out}")
        return count
    except Exception as e:
        print(f"  [FAIL] Medical Q&A: {e}")
        return 0


# ── Kaggle datasets ───────────────────────────────────────────────

def _kaggle_download(slug):
    import kaggle
    kaggle.api.authenticate()
    TEMP_DIR.mkdir(exist_ok=True)
    dest = TEMP_DIR / slug.replace("/", "_")
    dest.mkdir(exist_ok=True)
    print(f"  Downloading kaggle.com/datasets/{slug} ...")
    kaggle.api.dataset_download_files(slug, path=str(dest), unzip=True, quiet=False)
    return dest


def ingest_bbc_kaggle(max_articles=1000):
    """BBC News archive from Kaggle."""
    print_section(f"BBC News (Kaggle) ({max_articles} articles)")
    try:
        dest = _kaggle_download("hgultekin/bbcnewsarchive")
        out = DOCS_DIR / "news" / "bbc"
        count = 0
        for csv_file in dest.rglob("*.csv"):
            with open(csv_file, encoding="utf-8", errors="ignore") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if count >= max_articles:
                        break
                    text_col = next(
                        (k for k in row if k.lower() in ("text", "content", "article", "body", "description")),
                        None,
                    )
                    title_col = next(
                        (k for k in row if k.lower() in ("title", "headline", "subject")),
                        None,
                    )
                    if not text_col:
                        continue
                    title = row.get(title_col, f"article_{count}") if title_col else f"article_{count}"
                    body = f"# {title}\n\n{row[text_col]}"
                    save_txt(out, count, title, body)
                    count += 1
        print(f"  [OK] Saved {count} BBC articles -> {out}")
        return count
    except Exception as e:
        print(f"  [FAIL] BBC Kaggle: {e}")
        return 0


def ingest_arxiv_kaggle(max_papers=1000):
    """ArXiv metadata from Kaggle."""
    print_section(f"ArXiv Metadata (Kaggle) ({max_papers} papers)")
    try:
        dest = _kaggle_download("Cornell-University/arxiv")
        out = DOCS_DIR / "science" / "arxiv_kaggle"
        count = 0
        for json_file in dest.rglob("*.json"):
            with open(json_file, encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if count >= max_papers:
                        break
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    title = record.get("title", "").strip().replace("\n", " ")
                    abstract = record.get("abstract", "").strip().replace("\n", " ")
                    categories = record.get("categories", "")
                    if not abstract:
                        continue
                    body = f"# {title}\n\nCategories: {categories}\n\nAbstract: {abstract}"
                    save_txt(out, count, title, body)
                    count += 1
        print(f"  [OK] Saved {count} ArXiv papers -> {out}")
        return count
    except Exception as e:
        print(f"  [FAIL] ArXiv Kaggle: {e}")
        return 0


def ingest_news_kaggle(max_articles=1000):
    """HuffPost News Category Dataset from Kaggle."""
    print_section(f"HuffPost News (Kaggle) ({max_articles} articles)")
    try:
        dest = _kaggle_download("rmisra/news-category-dataset")
        out = DOCS_DIR / "news" / "huffpost"
        count = 0
        for json_file in dest.rglob("*.json*"):
            with open(json_file, encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if count >= max_articles:
                        break
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    headline = record.get("headline", "").strip()
                    short_desc = record.get("short_description", "").strip()
                    category = record.get("category", "")
                    authors = record.get("authors", "")
                    if not headline:
                        continue
                    body = (
                        f"# {headline}\n\n"
                        f"Category: {category}\nAuthors: {authors}\n\n"
                        f"{short_desc}"
                    )
                    save_txt(out, count, headline, body)
                    count += 1
        print(f"  [OK] Saved {count} HuffPost articles -> {out}")
        return count
    except Exception as e:
        print(f"  [FAIL] News Kaggle: {e}")
        return 0


# ── Summary ───────────────────────────────────────────────────────

def print_summary():
    total_files = sum(1 for _ in DOCS_DIR.rglob("*.txt"))
    total_size = sum(f.stat().st_size for f in DOCS_DIR.rglob("*.txt"))
    print("\n" + "=" * 60)
    print("  INGESTION COMPLETE")
    print("=" * 60)
    print(f"  Documents folder : {DOCS_DIR.resolve()}")
    print(f"  Total .txt files : {total_files:,}")
    print(f"  Total size       : {total_size / 1024 / 1024:.1f} MB")
    print("\n  Breakdown by category:")
    for subdir in sorted(DOCS_DIR.iterdir()):
        if subdir.is_dir():
            n = sum(1 for _ in subdir.rglob("*.txt"))
            print(f"    {subdir.name:<20} {n:>5} files")
    print("\n  Next step: restart the server (or click Rebuild Index in the UI).")
    print("=" * 60)


# ── Orchestrator ──────────────────────────────────────────────────

def run(source="auto", max_per_dataset=500, clear=False):
    print("\n" + "=" * 60)
    print("  RAG DATASET INGESTION")
    print("=" * 60)
    print(f"  Source  : {source}")
    print(f"  Max/set : {max_per_dataset}")

    if clear and DOCS_DIR.exists():
        print(f"\n  Clearing {DOCS_DIR} ...")
        shutil.rmtree(DOCS_DIR)
    DOCS_DIR.mkdir(exist_ok=True)

    has_kaggle = check_kaggle()
    if not has_kaggle and source == "kaggle":
        print("\n  [!] No Kaggle credentials found.")
        print("      To use Kaggle datasets:")
        print("      1. Go to https://www.kaggle.com/settings -> Create New Token")
        print("      2. Place kaggle.json at C:\\Users\\<you>\\.kaggle\\kaggle.json")
        sys.exit(1)
    elif not has_kaggle and source == "auto":
        print("\n  [!] No Kaggle credentials found - using HuggingFace only.")
        print("      To enable Kaggle: place kaggle.json at ~/.kaggle/kaggle.json")

    total = 0

    if source in ("kaggle", "auto") and has_kaggle:
        total += ingest_bbc_kaggle(max_per_dataset)
        total += ingest_arxiv_kaggle(max_per_dataset)
        total += ingest_news_kaggle(max_per_dataset)

    if source in ("hf", "auto") or (source == "kaggle" and not has_kaggle):
        total += ingest_wikipedia(max_per_dataset)
        total += ingest_ag_news(max_per_dataset)
        total += ingest_arxiv_hf(min(max_per_dataset, 300))
        total += ingest_squad_passages(min(max_per_dataset, 300))
        total += ingest_medical_hf(min(max_per_dataset, 200))

    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)

    print_summary()
    return total


# ── CLI ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Download real-world datasets into documents/ for RAG.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            examples:
              python ingest.py                   # auto mode
              python ingest.py --source hf       # HuggingFace only (no account)
              python ingest.py --source kaggle   # Kaggle only
              python ingest.py --max 200         # 200 docs per dataset
              python ingest.py --clear           # wipe documents/ first
        """),
    )
    parser.add_argument("--source", choices=["auto", "hf", "kaggle"], default="auto")
    parser.add_argument("--max", type=int, default=500, dest="max_per_dataset")
    parser.add_argument("--clear", action="store_true")
    parser.add_argument("--list", action="store_true")

    args = parser.parse_args()

    if args.list:
        print("\nAvailable datasets:")
        print("\n  HuggingFace (no account needed):")
        print("    wikipedia    - Simple English Wikipedia articles")
        print("    ag_news      - AG News (world, sports, business, tech)")
        print("    arxiv        - ArXiv CS paper abstracts")
        print("    squad        - SQuAD reading comprehension passages")
        print("    medical      - Medical Q&A")
        print("\n  Kaggle (requires ~/.kaggle/kaggle.json):")
        print("    bbc          - BBC News full article text")
        print("    arxiv_kaggle - ArXiv metadata (500K+ papers)")
        print("    huffpost     - HuffPost news category dataset")
        sys.exit(0)

    run(source=args.source, max_per_dataset=args.max_per_dataset, clear=args.clear)
