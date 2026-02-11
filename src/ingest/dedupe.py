from __future__ import annotations

import hashlib

from src.core.utils import normalize_text
from src.domain.models import JobPosting


def job_fingerprint(job: JobPosting) -> str:
    base = "|".join(
        [
            normalize_text(job.company),
            normalize_text(job.title),
            normalize_text(job.location),
            normalize_text(job.description[:300]),
        ]
    )
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def dedupe_jobs(jobs: list[JobPosting]) -> list[JobPosting]:
    seen: set[str] = set()
    unique: list[JobPosting] = []
    for job in jobs:
        fp = job_fingerprint(job)
        if fp in seen:
            continue
        seen.add(fp)
        unique.append(job)
    return unique
