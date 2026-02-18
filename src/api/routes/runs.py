from typing import Any

from fastapi import APIRouter, Depends
from sqlmodel import Session

from src.api.deps import get_db_session
from src.core.config import get_settings
from src.tracker.repo import TrackerRepository

router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("")
def list_runs(session: Session = Depends(get_db_session)) -> list[Any]:
    settings = get_settings()
    return TrackerRepository(session).list_runs(user_id=settings.user_id)
