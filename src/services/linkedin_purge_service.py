from __future__ import annotations

from typing import Any

from src.tracker.repo import TrackerRepository


def purge_low_fit_linkedin_jobs(repo: TrackerRepository, user_id: str, limit: int = 20) -> dict[str, Any]:
    executions = repo.list_execution_runs(user_id=user_id)
    purged: list[dict[str, str]] = []

    for job in repo.list_jobs_all(min_score=0, user_id=user_id):
        if len(purged) >= limit:
            break
        if job.source != "linkedin":
            continue
        if job.recommendation != "SKIP" or job.score > 40:
            continue

        application = repo.get_application_by_job(job.id, user_id=user_id)
        if application is not None and application.status not in {"new", "prepared"}:
            continue

        related_executions = [row for row in executions if row.job_id == job.id]
        if any(row.status in {"completed", "paused", "applying", "preparing"} for row in related_executions):
            continue

        if repo.delete_job_bundle(job.id, user_id=user_id):
            purged.append(
                {
                    "id": job.id,
                    "title": job.title,
                    "company": job.company,
                }
            )

    return {
        "status": "completed",
        "message": f"Foram removidas {len(purged)} vagas LinkedIn de baixo fit.",
        "purged_jobs": purged,
    }
