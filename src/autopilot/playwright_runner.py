from __future__ import annotations

from pathlib import Path

from src.autopilot.detectors import detect_captcha_or_auth
from src.domain.pause_control import build_pause_context


def run_autopilot_preview(
    application_url: str,
    resume_path: Path,
    html_snapshot: str,
    allow_submit: bool = False,
) -> dict[str, str]:
    detector = detect_captcha_or_auth(html_snapshot)
    if detector:
        return {
            "application_url": application_url,
            "resume_path": str(resume_path),
            "status": "paused",
            "summary": f"Execucao pausada por {detector}.",
            **build_pause_context(detector),
        }

    if allow_submit:
        return {
            "application_url": application_url,
            "resume_path": str(resume_path),
            "status": "completed",
            "summary": "Submissao final executada apos retomada autorizada.",
        }

    return {
        "application_url": application_url,
        "resume_path": str(resume_path),
        "status": "paused",
        "summary": "Campos basicos preenchidos; aguardando aprovacao humana antes de enviar.",
        **build_pause_context("manual_review_before_submit"),
    }
