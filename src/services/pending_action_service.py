from __future__ import annotations

from typing import Any

from src.domain.pause_control import build_pause_context
from src.services.execution_view_service import serialize_execution
from src.tracker.repo import TrackerRepository


def list_pending_actions(repo: TrackerRepository, user_id: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []

    for execution in repo.list_execution_runs(status="paused", user_id=user_id):
        payload = serialize_execution(execution)
        items.append(
            {
                "kind": "execution_pause",
                "id": execution.id,
                "application_id": execution.application_id,
                "job_id": execution.job_id,
                "title": f"{execution.connector} pausado em {execution.current_step}",
                "status": execution.status,
                "pause_reason": payload.get("pause_reason", ""),
                "recommended_action": payload.get("recommended_action", ""),
                "updated_at": execution.updated_at,
            }
        )

    for event in repo.list_email_events(user_id=user_id):
        if not event.action_required:
            continue
        pause = build_pause_context("manual_review_before_submit", detail=event.subject)
        items.append(
            {
                "kind": "email_followup",
                "id": event.id,
                "application_id": event.application_id,
                "job_id": repo.get_application(event.application_id, user_id=user_id).job_id if repo.get_application(event.application_id, user_id=user_id) else "",
                "title": event.subject,
                "status": event.status_inferred,
                "pause_reason": "email_action_required",
                "recommended_action": f"Revisar a inbox e responder ao contato recebido. {pause['recommended_action']}",
                "updated_at": event.received_at,
            }
        )

    items.sort(key=lambda item: item["updated_at"], reverse=True)
    return items
