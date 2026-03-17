from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from uuid import uuid4

from src.autopilot.connectors import ApplicationContext, BaseConnector, choose_connector
from src.core.config import Settings
from src.domain.anchors import extract_job_anchors
from src.domain.models import ApplicationRecord, CandidateProfile, ConfidenceLevel, ExecutionCheckpoint, ExecutionStatus, GeneratedAnswer, JobPosting
from src.domain.pause_control import build_pause_context
from src.domain.scoring import score_job
from src.domain.tailoring import build_artifacts
from src.services.llm_service import generate_application_intelligence
from src.services.operation_policy_service import evaluate_operation_policy
from src.services.profile_brain_service import get_effective_profile
from src.tracker.repo import ExecutionRunTable, TrackerRepository

PIPELINE_STEPS = (
    "prepare",
    "fill_form",
    "upload_artifacts",
    "answer_questions",
    "submit",
    "checkpoint",
)


def generate_application_answers(job_title: str, company: str, job_description: str = "") -> list[GeneratedAnswer]:
    answers = [
        GeneratedAnswer(
            question="Why are you interested in this role?",
            answer=f"I am targeting roles like {job_title} and see a strong fit between my background and {company}.",
            confidence=ConfidenceLevel.HIGH,
            rationale="Uses target role and company context from the saved profile.",
        ),
        GeneratedAnswer(
            question="What is your notice period?",
            answer="I can discuss start date quickly and align to the company's hiring timeline.",
            confidence=ConfidenceLevel.MEDIUM,
            rationale="Safe default without inventing legal or contractual details.",
        ),
        GeneratedAnswer(
            question="Can you share a short fit summary?",
            answer=f"My profile is strongest in hands-on delivery, product mindset and practical execution for teams like {company}.",
            confidence=ConfidenceLevel.MEDIUM,
            rationale="Summarizes fit in a reusable application-safe way.",
        ),
    ]
    description = job_description.lower()
    if any(hint in description for hint in ("salary expectation", "expected salary", "pretensao salarial", "desired compensation")):
        answers.append(
            GeneratedAnswer(
                question="What is your salary expectation?",
                answer="I prefer to calibrate compensation with the full scope of the role and total package.",
                confidence=ConfidenceLevel.LOW,
                rationale="Compensation expectations must be confirmed manually before submission.",
            )
        )
    return answers


def enrich_answers_with_guardrails(answers: list[GeneratedAnswer], job_description: str) -> list[GeneratedAnswer]:
    description = job_description.lower()
    has_salary_guardrail = any("salary" in answer.question.lower() or "pretens" in answer.question.lower() for answer in answers)
    if not has_salary_guardrail and any(hint in description for hint in ("salary expectation", "expected salary", "pretensao salarial", "desired compensation")):
        answers.append(
            GeneratedAnswer(
                question="What is your salary expectation?",
                answer="I prefer to calibrate compensation with the full scope of the role and total package.",
                confidence=ConfidenceLevel.LOW,
                rationale="Compensation expectations must be confirmed manually before submission.",
            )
        )
    return answers


def prepare_application_assets(repo: TrackerRepository, settings: Settings, job_id: str, user_id: str) -> tuple[str, list[GeneratedAnswer], str]:
    application = repo.get_application_by_job(job_id, user_id=user_id)
    job = repo.get_job(job_id)
    if application is None or job is None:
        raise ValueError("application or job not found")

    effective_profile = get_effective_profile(repo, settings.profile_path, user_id)
    existing_artifacts = repo.list_application_artifacts(application.id, user_id=user_id)
    existing_answers = repo.list_application_answers(application.id, user_id=user_id)
    if existing_artifacts and existing_answers:
        resume_artifact = next((artifact for artifact in existing_artifacts if artifact.kind == "resume"), existing_artifacts[0])
        fit_artifact = next((artifact for artifact in existing_artifacts if artifact.kind == "fit_summary"), None)
        answers = [
            GeneratedAnswer(
                question=row.question,
                answer=row.answer,
                confidence=ConfidenceLevel(row.confidence),
                rationale=row.rationale,
            )
            for row in existing_answers
        ]
        return resume_artifact.path, answers, fit_artifact.content if fit_artifact else ""

    profile = effective_profile
    job_posting = JobPosting(
        external_id=job.external_id,
        source=job.source,
        url=job.url,
        title=job.title,
        company=job.company,
        location=job.location,
        description=job.description,
        requirements=[],
    )
    anchors = extract_job_anchors(job_posting)
    scoring = score_job(job_posting, profile)
    bundle = build_artifacts(job_posting, profile, settings.artifacts_dir, anchors, scoring, settings.profile_dynamic_path)

    artifacts = {
        "resume": bundle.resume_path,
        "cover_letter": bundle.cover_paths[1] if bundle.cover_paths else bundle.resume_path,
        "email": bundle.email_path,
        "checklist": bundle.checklist_path,
    }
    for kind, path in artifacts.items():
        content = Path(path).read_text(encoding="utf-8")
        repo.create_application_artifact(
            artifact_id=str(uuid4()),
            application_id=application.id,
            job_id=job_id,
            kind=kind,
            label=Path(path).name,
            path=path,
            content=content,
            user_id=user_id,
        )
    intelligence = generate_application_intelligence(settings, profile, job_posting)
    answers = intelligence.answers or generate_application_answers(job.title, job.company, job.description)
    answers = enrich_answers_with_guardrails(answers, job.description)
    for answer in answers:
        repo.create_application_answer(
            answer_id=str(uuid4()),
            application_id=application.id,
            job_id=job_id,
            question=answer.question,
            answer=answer.answer,
            confidence=answer.confidence.value,
            rationale=answer.rationale,
            user_id=user_id,
        )
    fit_summary = intelligence.fit_summary or f"Fit summary unavailable for {job.title} at {job.company}."
    repo.create_application_artifact(
        artifact_id=str(uuid4()),
        application_id=application.id,
        job_id=job_id,
        kind="fit_summary",
        label=f"fit_summary_{job_id}.txt",
        path="",
        content=fit_summary,
        user_id=user_id,
    )
    return artifacts["resume"], answers, fit_summary


def _build_step_handlers(
    connector: BaseConnector,
    answers: list[GeneratedAnswer],
    allow_submit: bool,
) -> dict[str, Callable[[ApplicationContext], object]]:
    def answer_step(context: ApplicationContext) -> object:
        low_confidence = [answer for answer in answers if answer.confidence == ConfidenceLevel.LOW]
        if low_confidence:
            lead = low_confidence[0]
            pause = build_pause_context("low_confidence_answer", detail=lead.question)
            return ExecutionCheckpoint(
                step="answer_questions",
                status="paused",
                message=f"Resposta de baixa confianca detectada: {lead.question}",
                payload={
                    "question": lead.question,
                    "confidence": lead.confidence.value,
                    **pause,
                },
            )
        return connector.answer_questions(context)

    return {
        "prepare": connector.prepare,
        "fill_form": connector.fill_form,
        "upload_artifacts": connector.upload_artifacts,
        "answer_questions": answer_step,
        "submit": lambda context: connector.submit(context, allow_submit=allow_submit),
        "checkpoint": connector.checkpoint,
    }


def _determine_start_step(execution: ExecutionRunTable) -> int:
    if execution.current_step not in PIPELINE_STEPS:
        return 0
    current_index = PIPELINE_STEPS.index(execution.current_step)
    if execution.status == ExecutionStatus.PAUSED.value:
        return current_index
    return min(current_index + 1, len(PIPELINE_STEPS))


def _is_paused_checkpoint(checkpoint: object) -> bool:
    return getattr(checkpoint, "status", "") == "paused"


def _pause_metadata(checkpoint: object) -> tuple[str, str]:
    payload = getattr(checkpoint, "payload", {}) or {}
    return str(payload.get("pause_reason", "")), str(payload.get("recommended_action", ""))


def _record_execution_event(repo: TrackerRepository, execution_id: str, checkpoint: object, user_id: str) -> None:
    repo.create_execution_event(
        event_id=str(uuid4()),
        run_id=execution_id,
        step=checkpoint.step,
        status=checkpoint.status,
        message=checkpoint.message,
        payload=checkpoint.payload,
        screenshot_path=checkpoint.screenshot_path or "",
        snapshot_path=checkpoint.snapshot_path or "",
        user_id=user_id,
    )


def _finalize_execution(
    repo: TrackerRepository,
    settings: Settings,
    execution: ExecutionRunTable,
    connector: BaseConnector,
    job_id: str,
    user_id: str,
    final_status: str,
    next_application_status: str,
    pause_reason: str = "",
    error_message: str = "",
) -> None:
    repo.update_execution_run(
        execution.id,
        status=final_status,
        pause_reason=pause_reason,
        error_message=error_message,
    )
    repo.update_application_status(job_id, next_application_status, notes=f"connector={connector.connector_type.value}", user_id=user_id)
    repo.upsert_browser_session(
        session_id=f"{user_id}:{connector.connector_type.value}",
        platform=connector.connector_type.value,
        state="warm" if final_status != ExecutionStatus.FAILED.value else "stale",
        profile_dir=str(settings.browser_storage_dir / connector.connector_type.value),
        last_error=error_message,
        user_id=user_id,
    )
    repo.upsert_platform_credential_state(
        platform=connector.connector_type.value,
        state="needs_review" if final_status == ExecutionStatus.PAUSED.value else "ready",
        detail=pause_reason or "Connector execution completed.",
        user_id=user_id,
    )


def _run_pipeline(
    repo: TrackerRepository,
    settings: Settings,
    execution: ExecutionRunTable,
    connector: BaseConnector,
    context: ApplicationContext,
    user_id: str,
    allow_submit: bool,
    answers: list[GeneratedAnswer],
) -> str:
    policy = evaluate_operation_policy(repo, settings, connector.connector_type.value, user_id)
    if not policy["allowed"]:
        repo.create_execution_event(
            event_id=str(uuid4()),
            run_id=execution.id,
            step=execution.current_step,
            status="paused",
            message=policy["message"],
            payload={
                "pause_reason": policy["reason"],
                "recommended_action": policy["recommended_action"],
            },
            user_id=user_id,
        )
        _finalize_execution(
            repo,
            settings,
            execution,
            connector,
            execution.job_id,
            user_id,
            final_status=ExecutionStatus.PAUSED.value,
            next_application_status="reviewed",
            pause_reason=policy["reason"],
        )
        return ExecutionStatus.PAUSED.value

    start_index = _determine_start_step(execution)
    step_handlers = _build_step_handlers(connector, answers=answers, allow_submit=allow_submit)
    final_status = ExecutionStatus.COMPLETED.value
    next_application_status = "applied"
    pause_reason = ""
    error_message = ""

    repo.update_execution_run(
        execution.id,
        status=ExecutionStatus.APPLYING.value if start_index else ExecutionStatus.PREPARING.value,
        current_step=PIPELINE_STEPS[start_index] if start_index < len(PIPELINE_STEPS) else execution.current_step,
        pause_reason="",
        error_message="",
        increment_retry=execution.status in {ExecutionStatus.PAUSED.value, ExecutionStatus.FAILED.value},
    )

    try:
        for step in PIPELINE_STEPS[start_index:]:
            checkpoint = step_handlers[step](context)
            _record_execution_event(repo, execution.id, checkpoint, user_id)
            repo.update_execution_run(execution.id, current_step=step)
            if _is_paused_checkpoint(checkpoint):
                final_status = ExecutionStatus.PAUSED.value
                next_application_status = "reviewed"
                pause_reason, _ = _pause_metadata(checkpoint)
                break
            if checkpoint.status == "failed":
                final_status = ExecutionStatus.FAILED.value
                next_application_status = "prepared"
                error_message = checkpoint.message
                break
    except Exception as exc:
        final_status = ExecutionStatus.FAILED.value
        next_application_status = "prepared"
        error_message = str(exc)
        repo.create_execution_event(
            event_id=str(uuid4()),
            run_id=execution.id,
            step=execution.current_step,
            status="failed",
            message=error_message,
            payload={"exception": exc.__class__.__name__},
            user_id=user_id,
        )
    finally:
        connector.close()

    _finalize_execution(
        repo,
        settings,
        execution,
        connector,
        execution.job_id,
        user_id,
        final_status=final_status,
        next_application_status=next_application_status,
        pause_reason=pause_reason,
        error_message=error_message,
    )
    return final_status


def execute_application(repo: TrackerRepository, settings: Settings, job_id: str, user_id: str, trigger: str = "manual") -> dict[str, object]:
    job = repo.get_job(job_id)
    if job is None:
        raise ValueError("job not found")
    application = repo.get_application_by_job(job_id, user_id=user_id)
    if application is None:
        application = repo.upsert_application(
            ApplicationRecord(id=f"app-{job_id}", job_id=job_id, status="prepared"),
            link=job.url,
            user_id=user_id,
            connector=choose_connector(job.url).connector_type.value,
        )

    connector = choose_connector(job.url)
    execution = repo.create_execution_run(
        execution_id=str(uuid4()),
        application_id=application.id,
        job_id=job_id,
        connector=connector.connector_type.value,
        phase="application",
        status=ExecutionStatus.QUEUED.value,
        trigger=trigger,
        user_id=user_id,
    )
    resume_path, answers, fit_summary = prepare_application_assets(repo, settings, job_id, user_id)
    context = ApplicationContext(
        application_url=job.url,
        resume_path=Path(resume_path),
        html_snapshot=job.description,
        browser_profile_dir=settings.browser_storage_dir / connector.connector_type.value,
        artifacts_dir=settings.artifacts_dir,
        live_browser_enabled=settings.live_browser_enabled,
        headless=settings.playwright_headless,
        answers={answer.question: answer.answer for answer in answers} | {"fit_summary": fit_summary},
        effective_profile=_effective_profile_context(get_effective_profile(repo, settings.profile_path, user_id), fit_summary),
    )
    final_status = _run_pipeline(repo, settings, execution, connector, context, user_id, allow_submit=False, answers=answers)
    refreshed = repo.get_execution_run(execution.id, user_id=user_id)
    return {
        "execution_id": execution.id,
        "application_id": application.id,
        "job_id": job_id,
        "connector": connector.connector_type.value,
        "status": final_status,
        "answers_generated": len(answers),
        "fit_summary": fit_summary,
        "current_step": refreshed.current_step if refreshed else execution.current_step,
        "pause_reason": refreshed.pause_reason if refreshed else "",
        "recommended_action": build_pause_context(refreshed.pause_reason)["recommended_action"] if refreshed and refreshed.pause_reason else "",
        "retry_count": refreshed.retry_count if refreshed else 0,
    }


def resume_execution(repo: TrackerRepository, settings: Settings, execution_id: str, user_id: str) -> dict[str, object]:
    execution = repo.get_execution_run(execution_id, user_id=user_id)
    if execution is None:
        raise ValueError("execution not found")
    job = repo.get_job(execution.job_id)
    if job is None:
        raise ValueError("job not found")

    connector = choose_connector(job.url)
    resume_path, answers, fit_summary = prepare_application_assets(repo, settings, execution.job_id, user_id)
    context = ApplicationContext(
        application_url=job.url,
        resume_path=Path(resume_path),
        html_snapshot=job.description,
        browser_profile_dir=settings.browser_storage_dir / connector.connector_type.value,
        artifacts_dir=settings.artifacts_dir,
        live_browser_enabled=settings.live_browser_enabled,
        headless=settings.playwright_headless,
        answers={answer.question: answer.answer for answer in answers} | {"fit_summary": fit_summary},
        effective_profile=_effective_profile_context(get_effective_profile(repo, settings.profile_path, user_id), fit_summary),
    )
    final_status = _run_pipeline(repo, settings, execution, connector, context, user_id, allow_submit=True, answers=answers)
    refreshed = repo.get_execution_run(execution.id, user_id=user_id)
    return {
        "execution_id": execution.id,
        "application_id": execution.application_id,
        "job_id": execution.job_id,
        "connector": connector.connector_type.value,
        "status": final_status,
        "answers_generated": len(answers),
        "fit_summary": fit_summary,
        "current_step": refreshed.current_step if refreshed else execution.current_step,
        "pause_reason": refreshed.pause_reason if refreshed else "",
        "recommended_action": build_pause_context(refreshed.pause_reason)["recommended_action"] if refreshed and refreshed.pause_reason else "",
        "retry_count": refreshed.retry_count if refreshed else execution.retry_count,
    }


def apply_shortlist(repo: TrackerRepository, settings: Settings, user_id: str, limit: int = 5) -> dict[str, object]:
    jobs = shortlist_candidates(repo, user_id, limit)
    return _apply_job_batch(repo, settings, user_id, jobs, message_prefix="Shortlist executada")


def apply_selected_jobs(repo: TrackerRepository, settings: Settings, user_id: str, job_ids: list[str]) -> dict[str, object]:
    ordered_jobs = []
    seen: set[str] = set()
    for job_id in job_ids:
        if job_id in seen:
            continue
        seen.add(job_id)
        job = repo.get_job(job_id)
        if job is None or job.status != "new" or job.recommendation != "APPLY":
            continue
        ordered_jobs.append(job)
    return _apply_job_batch(repo, settings, user_id, ordered_jobs, message_prefix="Selecao executada")


def _apply_job_batch(repo: TrackerRepository, settings: Settings, user_id: str, jobs: list[object], message_prefix: str) -> dict[str, object]:
    results: list[dict[str, object]] = []
    for job in jobs:
        application = repo.get_application_by_job(job.id, user_id=user_id)
        if application is not None and application.status not in {"new", "prepared", "reviewed"}:
            continue
        outcome = execute_application(repo, settings, job.id, user_id, trigger="shortlist")
        results.append(
            {
                "job_id": job.id,
                "title": job.title,
                "company": job.company,
                "status": outcome["status"],
                "execution_id": outcome["execution_id"],
                "pause_reason": outcome["pause_reason"],
            }
        )
        if outcome["pause_reason"] in {"auth_required", "session_invalid", "captcha_detected", "retry_backoff"}:
            break
    return {
        "status": "completed",
        "message": f"{message_prefix} para {len(results)} vagas APPLY.",
        "results": results,
    }


def shortlist_candidates(repo: TrackerRepository, user_id: str, limit: int = 5) -> list[object]:
    jobs = [
        row
        for row in repo.list_jobs_all(min_score=0, user_id=user_id)
        if row.status == "new" and row.recommendation == "APPLY"
    ]
    return sorted(jobs, key=lambda row: row.score, reverse=True)[:limit]


def _effective_profile_context(profile: CandidateProfile, fit_summary: str) -> dict[str, object]:
    return {
        "target_role": profile.target_role,
        "location": profile.location,
        "focus_stacks": profile.stacks[:6],
        "fit_summary": fit_summary,
    }
