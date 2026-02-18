from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlmodel import Session

from src.api.deps import get_db_session
from src.core.config import get_settings
from src.domain.reasons import APPROVED_REASONS, REJECTED_REASONS
from src.domain.signals import Signal, record_signal
from src.tracker.repo import TrackerRepository

router = APIRouter(prefix="/jobs", tags=["jobs"])


class DecisionInput(BaseModel):
    reason: str
    notes: str = ""


@router.get("")
def list_jobs(
    status: str = Query(default="new"),
    min_score: int = Query(default=70),
    explore: bool = Query(default=False),
    session: Session = Depends(get_db_session),
) -> list[Any]:
    settings = get_settings()
    if explore:
        rows = TrackerRepository(session).list_recommendations(
            min_score=min_score,
            user_id=settings.user_id,
            explore=True,
        )
        return [{"job": item["job"], "is_exploration": item["is_exploration"]} for item in rows]

    return TrackerRepository(session).list_jobs(
        min_score=min_score,
        status=status,
        user_id=settings.user_id,
    )


@router.get("/{job_id}")
def get_job(job_id: str, session: Session = Depends(get_db_session)) -> Any:
    job = TrackerRepository(session).get_job(job_id)
    return job or {"detail": "job not found"}


@router.post("/{job_id}/approve")
def approve_job(
    job_id: str,
    payload: DecisionInput,
    session: Session = Depends(get_db_session),
) -> Any:
    if payload.reason not in APPROVED_REASONS:
        return {"detail": "invalid approve reason"}
    settings = get_settings()
    repo = TrackerRepository(session)
    row = repo.update_application_status(
        job_id,
        "approved",
        notes=payload.notes,
        user_id=settings.user_id,
    )
    record_signal(
        repo,
        Signal(
            signal_type="approval",
            job_id=job_id,
            payload={"reason": payload.reason, "notes": payload.notes},
            run_id="api",
            user_id=settings.user_id,
        ),
    )
    return row or {"detail": "application not found"}


@router.post("/{job_id}/reject")
def reject_job(
    job_id: str,
    payload: DecisionInput,
    session: Session = Depends(get_db_session),
) -> Any:
    if payload.reason not in REJECTED_REASONS:
        return {"detail": "invalid reject reason"}
    settings = get_settings()
    repo = TrackerRepository(session)
    row = repo.update_application_status(
        job_id,
        "rejected",
        notes=payload.notes,
        user_id=settings.user_id,
    )
    record_signal(
        repo,
        Signal(
            signal_type="rejection",
            job_id=job_id,
            payload={"reason": payload.reason, "notes": payload.notes},
            run_id="api",
            user_id=settings.user_id,
        ),
    )
    return row or {"detail": "application not found"}
