from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from src.core.config import Settings
from src.domain.pause_control import build_pause_context
from src.tracker.repo import TrackerRepository


def _today_prefix() -> str:
    return datetime.now(UTC).date().isoformat()


def count_applications_today(repo: TrackerRepository, connector: str, user_id: str) -> int:
    today = _today_prefix()
    rows = repo.list_applications(user_id=user_id)
    return len([row for row in rows if row.connector == connector and row.created_at.startswith(today)])


def count_total_applications_today(repo: TrackerRepository, user_id: str) -> int:
    today = _today_prefix()
    rows = repo.list_applications(user_id=user_id)
    return len([row for row in rows if row.created_at.startswith(today)])


def recent_failures(repo: TrackerRepository, connector: str, user_id: str, window_minutes: int = 30) -> int:
    threshold = datetime.now(UTC) - timedelta(minutes=window_minutes)
    count = 0
    for row in repo.list_execution_runs(user_id=user_id):
        if row.connector != connector or row.status != "failed":
            continue
        if datetime.fromisoformat(row.updated_at) >= threshold:
            count += 1
    return count


def evaluate_operation_policy(repo: TrackerRepository, settings: Settings, connector: str, user_id: str) -> dict[str, Any]:
    daily_total = count_total_applications_today(repo, user_id=user_id)
    daily_platform = count_applications_today(repo, connector, user_id=user_id)
    failures = recent_failures(repo, connector, user_id=user_id, window_minutes=settings.retry_backoff_window_minutes)
    session = next((row for row in repo.list_browser_sessions(user_id=user_id) if row.platform == connector), None)

    if daily_total >= settings.daily_application_limit:
        pause = build_pause_context("manual_review_before_submit", detail="daily_application_limit")
        return {
            "allowed": False,
            "reason": "daily_limit_reached",
            "message": f"Limite diario total atingido ({settings.daily_application_limit}).",
            "recommended_action": pause["recommended_action"],
        }
    if daily_platform >= settings.platform_application_limit:
        pause = build_pause_context("manual_review_before_submit", detail="platform_application_limit")
        return {
            "allowed": False,
            "reason": "platform_limit_reached",
            "message": f"Limite diario da plataforma {connector} atingido ({settings.platform_application_limit}).",
            "recommended_action": pause["recommended_action"],
        }
    if failures >= settings.max_retries_per_connector:
        return {
            "allowed": False,
            "reason": "retry_backoff",
            "message": f"Backoff ativo para {connector} apos {failures} falhas recentes.",
            "recommended_action": "Aguardar a janela de backoff expirar ou revisar a sessao da plataforma.",
        }
    if session is not None and session.state == "stale":
        pause = build_pause_context("session_invalid")
        return {
            "allowed": False,
            "reason": "session_invalid",
            "message": "Sessao persistente marcada como invalida para a plataforma.",
            "recommended_action": pause["recommended_action"],
        }
    return {
        "allowed": True,
        "daily_total": daily_total,
        "daily_platform": daily_platform,
        "recent_failures": failures,
    }


def operation_policy_snapshot(repo: TrackerRepository, settings: Settings, user_id: str) -> dict[str, Any]:
    connectors = sorted({row.connector for row in repo.list_applications(user_id=user_id)} | {row.platform for row in repo.list_browser_sessions(user_id=user_id)})
    return {
        "daily_application_limit": settings.daily_application_limit,
        "platform_application_limit": settings.platform_application_limit,
        "retry_backoff_window_minutes": settings.retry_backoff_window_minutes,
        "max_retries_per_connector": settings.max_retries_per_connector,
        "today_total": count_total_applications_today(repo, user_id=user_id),
        "connectors": [
            {
                "connector": connector,
                "today_count": count_applications_today(repo, connector, user_id=user_id),
                "recent_failures": recent_failures(repo, connector, user_id=user_id, window_minutes=settings.retry_backoff_window_minutes),
                "session_state": next((row.state for row in repo.list_browser_sessions(user_id=user_id) if row.platform == connector), "unknown"),
            }
            for connector in connectors
        ],
    }
