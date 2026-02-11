from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session

from src.api.deps import get_db_session
from src.core.config import get_settings
from src.domain.signals import Signal, record_signal
from src.tracker.repo import TrackerRepository

router = APIRouter(prefix="/applications", tags=["applications"])


class ApplicationStatusInput(BaseModel):
    status: str
    notes: str = ""


@router.post("/{job_id}/status")
def update_application_status(
    job_id: str,
    payload: ApplicationStatusInput,
    session: Session = Depends(get_db_session),
) -> Any:
    settings = get_settings()
    repo = TrackerRepository(session)
    updated = repo.update_application_status(
        job_id,
        payload.status,
        notes=payload.notes,
        user_id=settings.user_id,
    )
    if updated is None:
        return {"detail": "application not found"}
    record_signal(
        repo,
        Signal(
            signal_type=payload.status,
            job_id=job_id,
            payload={"notes": payload.notes},
            run_id="api",
            user_id=settings.user_id,
        ),
    )
    return updated
