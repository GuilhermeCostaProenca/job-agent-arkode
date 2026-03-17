from __future__ import annotations

from pathlib import Path
from typing import Any

from src.autopilot.linkedin_easy_apply import LinkedInPlaywrightRuntime
from src.autopilot.connectors import ApplicationContext, LinkedInConnector
from src.core.config import Settings
from src.domain.models import ConfidenceLevel, GeneratedAnswer
from src.domain.pause_control import build_pause_context
from src.services.profile_brain_service import get_effective_profile
from src.tracker.repo import TrackerRepository


def run_linkedin_session_setup(repo: TrackerRepository, settings: Settings, login_url: str = "https://www.linkedin.com/feed/") -> dict[str, Any]:
    runtime = LinkedInPlaywrightRuntime(
        profile_dir=settings.browser_storage_dir / "linkedin",
        artifacts_dir=settings.artifacts_dir,
        headless=settings.playwright_headless,
    )
    try:
        try:
            raw = runtime.setup_session(login_url, timeout_seconds=settings.linkedin_session_setup_timeout_seconds)
        except RuntimeError as exc:
            if str(exc) == "playwright_not_installed":
                result = {
                    "step": "prepare",
                    "status": "paused",
                    "message": "Playwright nao esta instalado no ambiente Python.",
                    "pause_reason": "browser_dependency_missing",
                    "recommended_action": build_pause_context("browser_dependency_missing")["recommended_action"],
                    "screenshot_path": "",
                    "snapshot_path": "",
                }
                _persist_session_state(repo, settings, result)
                return result
            raise

        result = {
            "step": "prepare",
            "status": raw["status"],
            "message": raw["summary"],
            "pause_reason": raw.get("pause_reason", ""),
            "recommended_action": raw.get("recommended_action", ""),
            "screenshot_path": raw.get("screenshot_path", ""),
            "snapshot_path": raw.get("snapshot_path", ""),
        }
        _persist_session_state(repo, settings, result)
        return result
    finally:
        runtime.close()


def run_linkedin_diagnostic(repo: TrackerRepository, settings: Settings, job_url: str) -> dict[str, Any]:
    connector = LinkedInConnector()
    context = _build_context(settings, job_url)
    try:
        prepare = connector.prepare(context)
        if prepare.status == "paused":
            result = _serialize_result("prepare", prepare)
            _persist_session_state(repo, settings, result)
            return result

        fill_form = connector.fill_form(context)
        if fill_form.status == "paused":
            result = _serialize_result("fill_form", fill_form)
            _persist_session_state(repo, settings, result)
            return result

        upload = connector.upload_artifacts(context)
        if upload.status == "paused":
            result = _serialize_result("upload_artifacts", upload)
            _persist_session_state(repo, settings, result)
            return result

        submit_preview = connector.submit(context, allow_submit=False)
        result = _serialize_result("submit", submit_preview)
        _persist_session_state(repo, settings, result)
        return result
    finally:
        connector.close()


def run_linkedin_discovery_preview(repo: TrackerRepository, settings: Settings, limit: int = 10) -> dict[str, Any]:
    profile = get_effective_profile(repo, settings.profile_path, settings.user_id)
    runtime = LinkedInPlaywrightRuntime(
        profile_dir=settings.browser_storage_dir / "linkedin",
        artifacts_dir=settings.artifacts_dir,
        headless=settings.playwright_headless,
    )
    try:
        jobs = runtime.scrape_job_recommendations(
            keywords=profile.target_role,
            location=profile.location,
            limit=limit,
            easy_apply_only=True,
        )
        return {
            "status": "completed",
            "message": f"Foram capturadas {len(jobs)} vagas do LinkedIn para o foco confirmado.",
            "effective_profile": {
                "target_role": profile.target_role,
                "location": profile.location,
                "stacks": profile.stacks,
            },
            "jobs": jobs,
        }
    except ValueError as exc:
        return {
            "status": "paused",
            "message": str(exc),
            "effective_profile": {
                "target_role": profile.target_role,
                "location": profile.location,
                "stacks": profile.stacks,
            },
            "jobs": [],
            **build_pause_context("auth_required"),
        }
    finally:
        runtime.close()


def _persist_session_state(repo: TrackerRepository, settings: Settings, result: dict[str, Any]) -> None:
    state = "ready"
    detail = result["message"]
    if result["status"] == "paused":
        pause_reason = result.get("pause_reason", "")
        if pause_reason in {"auth_required", "session_setup_required"}:
            state = "login_required"
        elif pause_reason == "session_invalid":
            state = "stale"
        else:
            state = "warm"
        detail = result.get("recommended_action", detail)

    repo.upsert_browser_session(
        session_id=f"{settings.user_id}:linkedin",
        platform="linkedin",
        state=state,
        profile_dir=str(settings.browser_storage_dir / "linkedin"),
        last_error="" if state == "ready" else result.get("pause_reason", ""),
        user_id=settings.user_id,
    )
    repo.upsert_platform_credential_state(
        platform="linkedin",
        state="ready" if state == "ready" else "needs_review",
        detail=detail,
        user_id=settings.user_id,
    )


def _serialize_result(step: str, checkpoint: Any) -> dict[str, Any]:
    return {
        "step": step,
        "status": checkpoint.status,
        "message": checkpoint.message,
        "pause_reason": checkpoint.payload.get("pause_reason", "") if getattr(checkpoint, "payload", None) else "",
        "recommended_action": checkpoint.payload.get("recommended_action", "") if getattr(checkpoint, "payload", None) else "",
        "screenshot_path": checkpoint.screenshot_path or "",
        "snapshot_path": checkpoint.snapshot_path or "",
    }


def _build_context(settings: Settings, job_url: str) -> ApplicationContext:
    return ApplicationContext(
        application_url=job_url,
        resume_path=_ensure_placeholder_resume(settings.artifacts_dir),
        html_snapshot="",
        browser_profile_dir=settings.browser_storage_dir / "linkedin",
        artifacts_dir=settings.artifacts_dir,
        live_browser_enabled=settings.live_browser_enabled,
        headless=settings.playwright_headless,
        answers=_default_answers(),
    )


def _ensure_placeholder_resume(artifacts_dir: Path) -> Path:
    diagnostics_dir = artifacts_dir / "diagnostics"
    diagnostics_dir.mkdir(parents=True, exist_ok=True)
    resume_path = diagnostics_dir / "linkedin-placeholder-resume.txt"
    if not resume_path.exists():
        resume_path.write_text("LinkedIn diagnostic placeholder resume.", encoding="utf-8")
    return resume_path


def _default_answers() -> dict[str, str]:
    answers = [
        GeneratedAnswer(
            question="Why are you interested in this role?",
            answer="I am a practical builder with hands-on delivery experience and strong product focus.",
            confidence=ConfidenceLevel.HIGH,
        ),
        GeneratedAnswer(
            question="Can you summarize your fit?",
            answer="I match well with execution-heavy engineering roles and can adapt quickly to business context.",
            confidence=ConfidenceLevel.HIGH,
        ),
    ]
    return {answer.question: answer.answer for answer in answers}
