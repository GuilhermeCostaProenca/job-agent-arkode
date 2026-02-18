from __future__ import annotations

from pathlib import Path

from src.autopilot.detectors import detect_captcha_or_auth


class AutopilotError(RuntimeError):
    pass


def run_autopilot_preview(
    application_url: str, resume_path: Path, html_snapshot: str
) -> dict[str, str]:
    detector = detect_captcha_or_auth(html_snapshot)
    if detector:
        raise AutopilotError(f"Autopilot pausado: {detector}. Necessária ação humana.")

    return {
        "application_url": application_url,
        "resume_path": str(resume_path),
        "status": "paused_before_submit",
        "summary": "Campos básicos preenchidos; aguardando aprovação humana antes de enviar.",
    }
