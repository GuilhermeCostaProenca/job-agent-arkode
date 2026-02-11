from typing import Any

from fastapi import APIRouter, Depends
from sqlmodel import Session

from src.api.deps import get_db_session
from src.tracker.repo import TrackerRepository

router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("")
def list_runs(session: Session = Depends(get_db_session)) -> list[Any]:
    return TrackerRepository(session).list_runs()
