from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from src.api.deps import get_db_session
from src.tracker.repo import TrackerRepository

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("")
def list_jobs(
    status: str = Query(default="new"),
    min_score: int = Query(default=70),
    session: Session = Depends(get_db_session),
) -> list[Any]:
    return TrackerRepository(session).list_jobs(min_score=min_score, status=status)


@router.get("/{job_id}")
def get_job(job_id: str, session: Session = Depends(get_db_session)) -> Any:
    job = TrackerRepository(session).get_job(job_id)
    return job or {"detail": "job not found"}
