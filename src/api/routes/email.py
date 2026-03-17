from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlmodel import Session

from src.api.deps import get_db_session
from src.core.config import get_settings
from src.services.email_sync_service import sync_email_events
from src.tracker.repo import TrackerRepository

router = APIRouter(prefix="/email", tags=["email"])


class EmailMessageInput(BaseModel):
    id: str = ""
    sender: str
    subject: str
    snippet: str


class EmailSyncInput(BaseModel):
    messages: list[EmailMessageInput] = Field(default_factory=list)


@router.post("/sync")
def sync_email(payload: EmailSyncInput, session: Session = Depends(get_db_session)) -> dict[str, int]:
    settings = get_settings()
    messages = [item.model_dump() for item in payload.messages]
    return sync_email_events(TrackerRepository(session), messages, settings.user_id)


@router.get("/events")
def list_email_events(session: Session = Depends(get_db_session)) -> list[object]:
    settings = get_settings()
    return TrackerRepository(session).list_email_events(user_id=settings.user_id)
