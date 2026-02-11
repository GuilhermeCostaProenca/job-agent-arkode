from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from src.core.config import get_settings
from src.core.ids import generate_job_id, generate_run_id
from src.domain.anchors import extract_job_anchors
from src.domain.models import ApplicationRecord, CandidateProfile, JobPosting
from src.domain.scoring import recommendation_from_score, score_job
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
            anchors = extract_job_anchors(job)
            job.anchors = anchors
            result = score_job(job, profile)
            job.score = result.score
            job.score_reasons = result.reasons
            job.score_breakdown = result.breakdown

            db_job_id = generate_job_id(job.source, job.external_id, job.company, job.title)
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
                anchors_json=anchors.model_dump_json(),
                score_breakdown_json=result.breakdown.model_dump_json(),
                recommendation=recommendation_from_score(result.score),
            )
            bundle = build_artifacts(
                job, profile, artifacts_dir or settings.artifacts_dir, anchors, result
            )
            repo.create_artifact(
                f"{run_id}-{db_job_id}-resume", run_id, db_job_id, "resume", bundle.resume_path
            )
            for idx, cover in enumerate(bundle.cover_paths):
                repo.create_artifact(
                    f"{run_id}-{db_job_id}-cover-{idx}", run_id, db_job_id, "cover", cover
                )
            repo.create_artifact(
                f"{run_id}-{db_job_id}-dm", run_id, db_job_id, "outreach_dm", bundle.dm_path
            )
            repo.create_artifact(
                f"{run_id}-{db_job_id}-email",
                run_id,
                db_job_id,
                "outreach_email",
                bundle.email_path,
            )
            repo.create_artifact(
                f"{run_id}-{db_job_id}-checklist",
                run_id,
                db_job_id,
                "checklist",
                bundle.checklist_path,
            )
            repo.create_artifact(
                f"{run_id}-{db_job_id}-match",
                run_id,
                db_job_id,
                "match_analysis",
                bundle.match_analysis_path,
            )
            repo.create_artifact(
                f"{run_id}-{db_job_id}-project",
                run_id,
                db_job_id,
                "project_prompt",
                bundle.project_prompt_path,
            )

            follow_up = datetime.now(UTC).date() + timedelta(days=5)
            repo.upsert_application(
                ApplicationRecord(
                    id=f"app-{db_job_id}",
                    job_id=db_job_id,
                    status="pending",
                    follow_up_date=follow_up,
                    recommendation=recommendation_from_score(result.score),
                ),
                link=job.url,
            )
        repo.finish_run(run_id, jobs_collected=len(jobs))
    return run_id


def export_jobs_csv(min_score: int, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = output_dir / f"applications_{datetime.now(UTC).date().isoformat()}.csv"
    with get_session() as session:
        rows = TrackerRepository(session).list_jobs_all(min_score=min_score)
    header = "job_id,empresa,título,score,recomendação,status,link\n"
    lines = [header]
    for row in rows:
        lines.append(
            f"{row.id},{row.company},{row.title},{row.score},{row.recommendation},{row.status},{row.url}\n"
        )
    filename.write_text("".join(lines), encoding="utf-8")
    return filename


def breakdown_for_job(job_row: object) -> dict[str, int]:
    data = getattr(job_row, "score_breakdown_json", "{}")
    raw = json.loads(data)
    return {
        str(k): int(v) for k, v in raw.items() if isinstance(k, str) and isinstance(v, int | float)
    }
