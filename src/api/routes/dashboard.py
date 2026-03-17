from fastapi import APIRouter, Depends
from sqlmodel import Session

from src.api.deps import get_db_session
from src.core.config import get_settings
from src.services.execution_view_service import serialize_execution
from src.services.operation_policy_service import operation_policy_snapshot
from src.services.pending_action_service import list_pending_actions
from src.tracker.repo import TrackerRepository

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
def get_dashboard(session: Session = Depends(get_db_session)) -> dict[str, object]:
    settings = get_settings()
    repo = TrackerRepository(session)
    summary = repo.dashboard_summary(user_id=settings.user_id)
    executions = repo.list_execution_runs(user_id=settings.user_id)
    summary["recent_executions"] = [serialize_execution(row) for row in executions[:8]]
    summary["paused_executions"] = [serialize_execution(row) for row in executions if row.status == "paused"][:8]
    shortlist_runs = [serialize_execution(row) for row in executions if getattr(row, "trigger", "") == "shortlist"][:8]
    summary["recent_shortlist_results"] = shortlist_runs
    summary["pending_actions"] = list_pending_actions(repo, settings.user_id)[:12]
    summary["operational_policy"] = operation_policy_snapshot(repo, settings, settings.user_id)
    return summary


@router.get("/pending-actions")
def get_pending_actions(session: Session = Depends(get_db_session)) -> list[dict[str, object]]:
    settings = get_settings()
    return list_pending_actions(TrackerRepository(session), settings.user_id)
