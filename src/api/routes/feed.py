from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session

from src.api.deps import get_db_session
from src.core.config import get_settings
from src.domain.hiring_signals import detect_hiring_signal
from src.domain.profile_loader import load_profile
from src.ingest.sources.feed_manual import load_feed_items_from_file, load_feed_items_from_url
from src.outreach.drafts import generate_outreach_drafts
from src.tracker.repo import TrackerRepository

router = APIRouter(prefix="/feed", tags=["feed"])


class FeedAddInput(BaseModel):
    url: str | None = None
    file: str | None = None


@router.post("")
def feed_add(payload: FeedAddInput, session: Session = Depends(get_db_session)) -> dict[str, int]:
    settings = get_settings()
    repo = TrackerRepository(session)
    items: list[dict[str, str]] = []
    if payload.url:
        items.extend(load_feed_items_from_url(payload.url))
    if payload.file:
        items.extend(load_feed_items_from_file(Path(payload.file)))
    for item in items:
        text = item.get("text") or item.get("url", "")
        result = detect_hiring_signal(text)
        repo.create_feed_item(
            feed_id=str(uuid4()),
            source=item.get("source", "manual"),
            url=item.get("url", ""),
            text=text,
            is_hiring=result.is_hiring,
            confidence=result.confidence,
            user_id=settings.user_id,
        )
    return {"inserted": len(items)}


@router.get("")
def feed_list(hiring_only: bool = True, session: Session = Depends(get_db_session)) -> list[Any]:
    settings = get_settings()
    return TrackerRepository(session).list_feed_items(
        hiring_only=hiring_only, user_id=settings.user_id
    )


@router.post("/{feed_id}/drafts")
def feed_drafts(feed_id: str, session: Session = Depends(get_db_session)) -> Any:
    settings = get_settings()
    repo = TrackerRepository(session)
    item = repo.get_feed_item(feed_id)
    if item is None:
        return {"detail": "feed item not found"}
    profile = load_profile(settings.profile_path)
    pref = repo.get_preference_model(user_id=settings.user_id) or {}
    style = pref.get("writing_style", {}) if isinstance(pref, dict) else {}
    drafts = generate_outreach_drafts(
        item.model_dump(),
        profile.model_dump(),
        style,
        settings.artifacts_dir,
    )
    return drafts
