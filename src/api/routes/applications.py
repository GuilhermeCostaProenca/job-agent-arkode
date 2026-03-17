from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session

from src.api.deps import get_db_session
from src.core.config import get_settings
from src.domain.signals import Signal, record_signal
from src.services.application_service import apply_selected_jobs, apply_shortlist, execute_application, shortlist_candidates
from src.services.execution_view_service import serialize_execution
from src.tracker.repo import TrackerRepository

router = APIRouter(prefix="/applications", tags=["applications"])


class ApplicationStatusInput(BaseModel):
    status: str
    notes: str = ""


class ApplyInput(BaseModel):
    job_id: str
    trigger: str = "manual"


class ShortlistApplyInput(BaseModel):
    limit: int = 5


class SelectedApplyInput(BaseModel):
    job_ids: list[str]


@router.post("/{job_id}/status")
def update_application_status(job_id: str, payload: ApplicationStatusInput, session: Session = Depends(get_db_session)) -> Any:
    settings = get_settings()
    repo = TrackerRepository(session)
    updated = repo.update_application_status(job_id, payload.status, notes=payload.notes, user_id=settings.user_id)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="application not found")
    record_signal(
        repo,
        Signal(signal_type=payload.status, job_id=job_id, payload={"notes": payload.notes}, run_id="api", user_id=settings.user_id),
    )
    return updated


@router.post("/apply")
def apply_to_job(payload: ApplyInput, session: Session = Depends(get_db_session)) -> dict[str, object]:
    settings = get_settings()
    return execute_application(TrackerRepository(session), settings, payload.job_id, settings.user_id, trigger=payload.trigger)


@router.post("/apply-shortlist")
def apply_shortlist_route(payload: ShortlistApplyInput, session: Session = Depends(get_db_session)) -> dict[str, object]:
    settings = get_settings()
    return apply_shortlist(TrackerRepository(session), settings, settings.user_id, limit=payload.limit)


@router.post("/apply-selected")
def apply_selected_route(payload: SelectedApplyInput, session: Session = Depends(get_db_session)) -> dict[str, object]:
    settings = get_settings()
    return apply_selected_jobs(TrackerRepository(session), settings, settings.user_id, payload.job_ids)


@router.get("/shortlist-preview")
def get_shortlist_preview(limit: int = 5, session: Session = Depends(get_db_session)) -> list[dict[str, object]]:
    settings = get_settings()
    jobs = shortlist_candidates(TrackerRepository(session), settings.user_id, limit=limit)
    return [
        {
            "job_id": row.id,
            "title": row.title,
            "company": row.company,
            "score": row.score,
            "source": row.source,
            "url": row.url,
        }
        for row in jobs
    ]


@router.get("")
def list_applications(status_filter: str | None = None, session: Session = Depends(get_db_session)) -> list[Any]:
    settings = get_settings()
    return TrackerRepository(session).list_applications(status=status_filter, user_id=settings.user_id)


@router.get("/followups")
def list_followups(session: Session = Depends(get_db_session)) -> list[Any]:
    settings = get_settings()
    today = datetime.now(UTC).date()
    return TrackerRepository(session).list_due_followups(today, user_id=settings.user_id)


@router.get("/{application_id}")
def get_application(application_id: str, session: Session = Depends(get_db_session)) -> dict[str, Any]:
    settings = get_settings()
    repo = TrackerRepository(session)
    application = repo.get_application(application_id, user_id=settings.user_id)
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="application not found")
    return {
        "application": application,
        "artifacts": repo.list_application_artifacts(application_id, user_id=settings.user_id),
        "answers": repo.list_application_answers(application_id, user_id=settings.user_id),
        "executions": [serialize_execution(row) for row in repo.list_execution_runs(user_id=settings.user_id) if row.application_id == application_id],
    }
