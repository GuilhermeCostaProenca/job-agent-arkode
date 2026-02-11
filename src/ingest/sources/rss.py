from __future__ import annotations

from datetime import UTC, datetime

import feedparser

from src.domain.models import JobPosting


def fetch_rss_jobs(feed_urls: list[str], limit: int = 30) -> list[JobPosting]:
    jobs: list[JobPosting] = []
    for url in feed_urls:
        parsed = feedparser.parse(url)
        for entry in parsed.entries[:limit]:
            job = JobPosting(
                external_id=getattr(entry, "id", entry.link),
                source="rss",
                url=entry.link,
                title=getattr(entry, "title", "Untitled role"),
                company=getattr(entry, "author", "Unknown Company"),
                location=getattr(entry, "location", "remote"),
                description=getattr(entry, "summary", ""),
                requirements=[],
                posted_at=datetime.now(UTC),
            )
            jobs.append(job)
            if len(jobs) >= limit:
                return jobs
    return jobs
