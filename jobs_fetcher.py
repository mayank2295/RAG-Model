"""
Jobs fetcher — Remotive API into Pinecone (namespace="jobs").

Pulls remote job listings for a fixed set of categories, strips HTML from
the description, embeds title + company + description, and upserts the
vectors into the "jobs" namespace.

Remotive requires no API key: https://remotive.com/api/remote-jobs
"""

import logging
from typing import Dict, List

import httpx
from bs4 import BeautifulSoup

import embedder
import vector_store

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("jobs_fetcher")

REMOTIVE_URL = "https://remotive.com/api/remote-jobs"
CATEGORIES = ("software-dev", "data", "devops")
LIMIT_PER_CATEGORY = 50
DESC_EMBED_CHARS = 500  # truncate description to 500 chars for embedding


def _strip_html(html: str) -> str:
    """Remove HTML tags and collapse whitespace from a job description."""
    if not html:
        return ""
    try:
        text = BeautifulSoup(html, "html.parser").get_text(separator=" ")
    except Exception:
        text = html
    return " ".join(text.split())


def _fetch_category(client: httpx.Client, category: str) -> List[Dict]:
    """Fetch remote jobs for one Remotive category."""
    try:
        resp = client.get(
            REMOTIVE_URL,
            params={"category": category, "limit": LIMIT_PER_CATEGORY},
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        logger.exception("Failed to fetch Remotive category '%s'.", category)
        return []
    return data.get("jobs", []) or []


def fetch_and_ingest_jobs() -> int:
    """
    Fetch remote jobs, embed them, and upsert into Pinecone (namespace="jobs").

    For each job we keep: title, company, url, published_date, tags. The
    description is stripped of HTML and truncated to 500 chars for embedding.
    Vector ids use the form "job_{id}". Duplicate ids are removed.

    Returns:
        The number of jobs ingested.
    """
    seen_ids: set[str] = set()
    vectors: List[Dict] = []

    with httpx.Client() as client:
        for category in CATEGORIES:
            jobs = _fetch_category(client, category)
            logger.info("Fetched %d jobs for category '%s'.", len(jobs), category)

            for job in jobs:
                job_id = job.get("id")
                if job_id is None:
                    continue
                vec_id = f"job_{job_id}"
                if vec_id in seen_ids:
                    continue
                seen_ids.add(vec_id)

                title = (job.get("title") or "").strip()
                company = (job.get("company_name") or "").strip()
                url = (job.get("url") or "").strip()
                published_date = (job.get("publication_date") or "").strip()
                tags = job.get("tags") or []
                description = _strip_html(job.get("description") or "")

                embed_input = f"{title} at {company}. {description}"[: DESC_EMBED_CHARS + 200]
                values = embedder.embed_text(embed_input[:DESC_EMBED_CHARS])

                vectors.append({
                    "id": vec_id,
                    "values": values,
                    "metadata": {
                        "title": title,
                        "company": company,
                        "url": url,
                        "published_date": published_date,
                        "tags": [str(t) for t in tags],
                        "category": category,
                    },
                })

    count = vector_store.upsert_vectors(vectors, namespace="jobs")
    logger.info("Jobs ingest complete — %d jobs upserted.", count)
    return count
