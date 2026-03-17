from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from src.core.config import get_settings
from src.core.ids import generate_job_id, generate_run_id
from src.domain.anchors import extract_job_anchors
from src.domain.dynamic_profile import update_dynamic_profile
from src.domain.models import ApplicationRecord, CandidateProfile, JobPosting
from src.domain.preference_engine import (
    apply_preferences_to_score,
    load_preference_model,
    update_preferences_from_signal,
)
from src.domain.scoring import recommendation_from_score, score_job
from src.domain.tailoring import build_artifacts
from src.ingest.dedupe import dedupe_jobs
from src.ingest.normalize import normalize_jobs
from src.ingest.sources.linkedin import fetch_linkedin_jobs
from src.ingest.sources.manual_url import fetch_manual_url
from src.ingest.sources.rss import fetch_rss_jobs
from src.services.job_fit_service import augment_job_fit_with_llm
from src.services.profile_brain_service import get_effective_profile
from src.tracker.db import get_session
from src.tracker.repo import TrackerRepository


def collect_jobs(
    sources: list[str], limit: int, rss_urls: list[str], manual_urls: list[str], profile: CandidateProfile
) -> list[JobPosting]:
    settings = get_settings()
    jobs: list[JobPosting] = []
    if "rss" in sources:
        jobs.extend(fetch_rss_jobs(rss_urls, limit=limit))
    if "manual" in sources:
        for url in manual_urls[:limit]:
            jobs.append(fetch_manual_url(url))
    if "linkedin" in sources:
        jobs.extend(fetch_linkedin_jobs(settings, profile, limit=limit))
    return dedupe_jobs(normalize_jobs(jobs))[:limit]


def _process_new_signals(repo: TrackerRepository, user_id: str) -> dict[str, Any]:
    pref_model = load_preference_model(repo, user_id=user_id)
    weights = pref_model.weights
    last_id = str(weights.get("last_processed_signal_id", ""))
    signals = repo.get_signals_after(last_id, user_id=user_id)
    for signal in signals:
        job = repo.get_job(signal.job_id)
        if job is None:
            continue
        anchors = extract_job_anchors(
            JobPosting(
                external_id=job.external_id,
                source=job.source,
                url=job.url,
                title=job.title,
                company=job.company,
                location=job.location,
                description=job.description,
            )
        )
        payload = json.loads(signal.payload_json) if signal.payload_json else {}

        class _SignalProxy:
            def __init__(self, signal_type: str, payload_json: dict[str, object], signal_id: str):
                self.signal_type = signal_type
                self.payload_json = payload_json
                self.id = signal_id

        proxy = _SignalProxy(signal.signal_type, payload, signal.id)
        weights = update_preferences_from_signal(proxy, job, anchors, weights)
    repo.upsert_preference_model("default", weights, user_id=user_id)
    return weights


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
    jobs = collect_jobs(sources, limit, rss_urls, manual_urls, profile)

    with get_session() as session:
        repo = TrackerRepository(session)
        repo.create_run(run_id, user_id=settings.user_id)
        effective_profile = get_effective_profile(repo, settings.profile_path, settings.user_id)
        learned_weights = _process_new_signals(repo, user_id=settings.user_id)
        for job in jobs:
            anchors = extract_job_anchors(job)
            job.anchors = anchors
            result = score_job(job, effective_profile)
            fit = augment_job_fit_with_llm(settings, effective_profile, job, result)
            result.fit_summary = fit.fit_summary
            result.recommendation = fit.recommendation
            result.llm_adjustment = fit.llm_adjustment
            result.reasons = fit.reasons
            result.gaps = fit.gaps
            result.top_matched_terms = fit.top_matched_terms
            result.score = max(0, min(100, result.score + fit.llm_adjustment))

            base_breakdown = result.breakdown.model_dump()
            adjusted_score, adjustments = apply_preferences_to_score(
                job,
                anchors,
                base_breakdown,
                learned_weights,
            )
            result.preference_adjustments = adjustments
            result.score = adjusted_score

            job.score = adjusted_score
            job.score_reasons = result.reasons + [f"llm_adjustment: {fit.llm_adjustment}", f"preferences: {adjustments}"]
            job.score_breakdown = result.breakdown

            existing_job = repo.get_job_by_external(job.source, job.external_id, user_id=settings.user_id)
            db_job_id = existing_job.id if existing_job is not None else generate_job_id(job.source, job.external_id, job.company, job.title)
            merged_breakdown = {**base_breakdown, "preference_adjustments": adjustments}
            repo.upsert_job(
                id=db_job_id,
                user_id=settings.user_id,
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
                score_breakdown_json=json.dumps(merged_breakdown, ensure_ascii=False),
                recommendation=result.recommendation,
            )
            bundle = build_artifacts(
                job,
                effective_profile,
                artifacts_dir or settings.artifacts_dir,
                anchors,
                result,
                settings.profile_dynamic_path,
            )
            repo.create_artifact(
                f"{run_id}-{db_job_id}-resume",
                run_id,
                db_job_id,
                "resume",
                bundle.resume_path,
                user_id=settings.user_id,
            )
            for idx, cover in enumerate(bundle.cover_paths):
                repo.create_artifact(
                    f"{run_id}-{db_job_id}-cover-{idx}",
                    run_id,
                    db_job_id,
                    "cover",
                    cover,
                    user_id=settings.user_id,
                )
            repo.create_artifact(
                f"{run_id}-{db_job_id}-dm",
                run_id,
                db_job_id,
                "outreach_dm",
                bundle.dm_path,
                user_id=settings.user_id,
            )
            repo.create_artifact(
                f"{run_id}-{db_job_id}-email",
                run_id,
                db_job_id,
                "outreach_email",
                bundle.email_path,
                user_id=settings.user_id,
            )
            repo.create_artifact(
                f"{run_id}-{db_job_id}-checklist",
                run_id,
                db_job_id,
                "checklist",
                bundle.checklist_path,
                user_id=settings.user_id,
            )
            repo.create_artifact(
                f"{run_id}-{db_job_id}-match",
                run_id,
                db_job_id,
                "match_analysis",
                bundle.match_analysis_path,
                user_id=settings.user_id,
            )
            repo.create_artifact(
                f"{run_id}-{db_job_id}-project",
                run_id,
                db_job_id,
                "project_prompt",
                bundle.project_prompt_path,
                user_id=settings.user_id,
            )

            follow_up = datetime.now(UTC).date() + timedelta(days=5)
            repo.upsert_application(
                ApplicationRecord(
                    id=f"app-{db_job_id}",
                    job_id=db_job_id,
                    status="prepared",
                    follow_up_date=follow_up,
                    recommendation=result.recommendation,
                ),
                link=job.url,
                user_id=settings.user_id,
            )
        repo.finish_run(run_id, jobs_collected=len(jobs))

        weights = load_preference_model(repo, user_id=settings.user_id).weights
        summary = repo.summarize_applications(user_id=settings.user_id)
        update_dynamic_profile(settings.profile_dynamic_path, weights, summary)
    return run_id


def export_jobs_csv(min_score: int, output_dir: Path) -> Path:
    settings = get_settings()
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = output_dir / f"applications_{datetime.now(UTC).date().isoformat()}.csv"
    with get_session() as session:
        rows = TrackerRepository(session).list_jobs_all(
            min_score=min_score, user_id=settings.user_id
        )
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
