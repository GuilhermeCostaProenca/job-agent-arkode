from __future__ import annotations

from src.domain.models import JobPosting


def crawl_careers_pages(urls: list[str], limit: int = 20) -> list[JobPosting]:
    """MVP stub for careers pages crawling; intentionally simple and safe."""
    jobs: list[JobPosting] = []
    for idx, url in enumerate(urls[:limit], start=1):
        jobs.append(
            JobPosting(
                external_id=f"careers-{idx}",
                source="careers_page",
                url=url,
                title="Role from careers page",
                company="Unknown",
                location="remote",
                description="Manual crawler placeholder. Use RSS/manual in MVP.",
            )
        )
    return jobs
