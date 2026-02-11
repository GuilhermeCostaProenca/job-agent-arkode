from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlmodel import Session

from src.api.deps import get_db_session
from src.core.config import get_settings
from src.domain.signals import Signal, record_signal
from src.tracker.repo import TrackerRepository

router = APIRouter(prefix="/signals", tags=["signals"])


class SignalInput(BaseModel):
    signal_type: str
    job_id: str
    payload: dict[str, Any] = Field(default_factory=dict)
    run_id: str = "api"


@router.post("")
def create_signal(payload: SignalInput, session: Session = Depends(get_db_session)) -> Any:
    settings = get_settings()
    repo = TrackerRepository(session)
    return record_signal(
        repo,
        Signal(
            signal_type=payload.signal_type,
            job_id=payload.job_id,
            payload=payload.payload,
            run_id=payload.run_id,
            user_id=settings.user_id,
        ),
    )


@router.get("")
def list_signals(limit: int = 50, session: Session = Depends(get_db_session)) -> list[Any]:
    settings = get_settings()
    return TrackerRepository(session).list_signals(limit=limit, user_id=settings.user_id)
