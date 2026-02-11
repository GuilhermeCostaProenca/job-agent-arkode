from typing import Any

from fastapi import APIRouter, Depends
from sqlmodel import Session

from src.api.deps import get_db_session
from src.tracker.repo import TrackerRepository

router = APIRouter(prefix="/artifacts", tags=["artifacts"])


@router.get("/{job_id}")
def list_artifacts(job_id: str, session: Session = Depends(get_db_session)) -> list[Any]:
    return TrackerRepository(session).list_artifacts(job_id)
