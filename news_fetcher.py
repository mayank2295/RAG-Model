"""
News fetcher — NewsAPI.org top headlines into Pinecone (namespace="news").

Pulls top headlines for a fixed set of categories, embeds each article's
title + description, and upserts the vectors into the "news" namespace.

Config (environment variables):
    NEWSAPI_KEY — NewsAPI.org API key
"""

import hashlib
import logging
import os
from typing import Dict, List

import httpx

import embedder
import vector_store

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("news_fetcher")

NEWSAPI_URL = "https://newsapi.org/v2/top-headlines"
CATEGORIES = ("technology", "business", "science")
PAGE_SIZE = 50  # articles per category per request


def _article_id(url: str) -> str:
    """Return a stable md5 hash of the article URL to use as the vector id."""
    return hashlib.md5(url.encode("utf-8")).hexdigest()


def _fetch_category(client: httpx.Client, api_key: str, category: str) -> List[Dict]:
    """Fetch top headlines for one category from NewsAPI."""
    try:
        resp = client.get(
            NEWSAPI_URL,
            params={
                "category": category,
                "language": "en",
                "pageSize": PAGE_SIZE,
                "apiKey": api_key,
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        logger.exception("Failed to fetch NewsAPI category '%s'.", category)
        return []

    if data.get("status") != "ok":
        logger.error("NewsAPI returned status '%s' for category '%s': %s",
                     data.get("status"), category, data.get("message"))
        return []

    return data.get("articles", []) or []


def fetch_and_ingest_news() -> int:
    """
    Fetch top headlines, embed them, and upsert into Pinecone (namespace="news").

    For each article we keep: title, description, url, publishedAt, source name.
    Articles with no description are skipped; duplicates (same URL) are removed.

    Returns:
        The number of news articles ingested.
    """
    api_key = os.environ.get("NEWSAPI_KEY")
    if not api_key:
        logger.error("NEWSAPI_KEY is not set — skipping news ingest.")
        return 0

    seen_urls: set[str] = set()
    vectors: List[Dict] = []

    with httpx.Client() as client:
        for category in CATEGORIES:
            articles = _fetch_category(client, api_key, category)
            logger.info("Fetched %d articles for category '%s'.", len(articles), category)

            for art in articles:
                url = (art.get("url") or "").strip()
                description = (art.get("description") or "").strip()
                title = (art.get("title") or "").strip()

                if not url or url in seen_urls:
                    continue
                if not description:
                    continue  # spec: skip articles with no description
                seen_urls.add(url)

                source_name = ((art.get("source") or {}).get("name") or "Unknown").strip()
                published_at = (art.get("publishedAt") or "").strip()

                text = f"{title}. {description}"
                values = embedder.embed_text(text)

                vectors.append({
                    "id": _article_id(url),
                    "values": values,
                    "metadata": {
                        "title": title,
                        "description": description,
                        "url": url,
                        "source": source_name,
                        "publishedAt": published_at,
                        "category": category,
                    },
                })

    count = vector_store.upsert_vectors(vectors, namespace="news")
    logger.info("News ingest complete — %d articles upserted.", count)
    return count
