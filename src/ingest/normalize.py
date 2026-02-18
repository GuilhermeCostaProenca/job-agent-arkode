from __future__ import annotations

from src.core.utils import normalize_text
from src.domain.models import JobPosting


def normalize_job(job: JobPosting) -> JobPosting:
    cleaned = job.model_copy(deep=True)
    cleaned.title = normalize_text(cleaned.title).title()
    cleaned.company = normalize_text(cleaned.company).title()
    cleaned.location = normalize_text(cleaned.location)
    cleaned.description = cleaned.description.strip()
    if not cleaned.requirements:
        lines = [line.strip("-• ") for line in cleaned.description.splitlines()]
        cleaned.requirements = [line for line in lines if len(line) > 20][:6]
    return cleaned


def normalize_jobs(jobs: list[JobPosting]) -> list[JobPosting]:
    return [normalize_job(job) for job in jobs]
