from __future__ import annotations

from pathlib import Path

from src.core.config import get_settings
from src.core.ids import generate_job_id, generate_run_id
from src.domain.models import CandidateProfile, JobPosting
from src.domain.scoring import score_job
from src.domain.tailoring import build_artifacts
from src.ingest.dedupe import dedupe_jobs
from src.ingest.normalize import normalize_jobs
from src.ingest.sources.manual_url import fetch_manual_url
from src.ingest.sources.rss import fetch_rss_jobs
from src.tracker.db import get_session
from src.tracker.repo import TrackerRepository


def collect_jobs(
    sources: list[str], limit: int, rss_urls: list[str], manual_urls: list[str]
) -> list[JobPosting]:
    jobs: list[JobPosting] = []
    if "rss" in sources:
        jobs.extend(fetch_rss_jobs(rss_urls, limit=limit))
    if "manual" in sources:
        for url in manual_urls[:limit]:
            jobs.append(fetch_manual_url(url))
    return dedupe_jobs(normalize_jobs(jobs))[:limit]


def run_pipeline(
    profile: CandidateProfile,
    sources: list[str],
    limit: int,
    rss_urls: list[str],
    manual_urls: list[str],
    artifacts_dir: Path | None = None,
) -> str:
    settings = get_settings()
    run_id = generate_run_id(settings.run_id_prefix)
    jobs = collect_jobs(sources, limit, rss_urls, manual_urls)

    with get_session() as session:
        repo = TrackerRepository(session)
        repo.create_run(run_id)
        for job in jobs:
            result = score_job(job, profile)
            job.score = result.score
            job.score_reasons = result.reasons
            db_job_id = generate_job_id(job.company, job.title)
            repo.upsert_job(
                id=db_job_id,
                run_id=run_id,
                external_id=job.external_id,
                source=job.source,
                url=job.url,
                title=job.title,
                company=job.company,
                location=job.location,
                description=job.description,
                score=job.score,
                score_reasons="\n".join(job.score_reasons),
            )
            bundle = build_artifacts(job, profile, artifacts_dir or settings.artifacts_dir)
            repo.create_artifact(
                f"{db_job_id}-resume", run_id, db_job_id, "resume", bundle.resume_path
            )
            for idx, cover in enumerate(bundle.cover_paths):
                repo.create_artifact(f"{db_job_id}-cover-{idx}", run_id, db_job_id, "cover", cover)
            repo.create_artifact(
                f"{db_job_id}-dm", run_id, db_job_id, "outreach_dm", bundle.dm_path
            )
            repo.create_artifact(
                f"{db_job_id}-email", run_id, db_job_id, "outreach_email", bundle.email_path
            )
            repo.create_artifact(
                f"{db_job_id}-checklist", run_id, db_job_id, "checklist", bundle.checklist_path
            )
        repo.finish_run(run_id, jobs_collected=len(jobs))
    return run_id
