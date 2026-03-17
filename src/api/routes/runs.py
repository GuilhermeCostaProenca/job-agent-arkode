from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import Session

from src.api.deps import get_db_session
from src.core.config import get_settings
from src.domain.pipeline import run_pipeline
from src.services.application_service import resume_execution
from src.services.profile_brain_service import get_effective_profile
from src.tracker.repo import RunTable, TrackerRepository

router = APIRouter(prefix="/runs", tags=["runs"])


class RunInput(BaseModel):
    sources: list[str] = Field(default_factory=lambda: ["rss", "manual", "linkedin"])
    limit: int = Field(default=30, ge=1, le=200)
    rss_feed: str = "https://remoteok.com/remote-dev-jobs.rss"
    manual_urls: list[str] = Field(default_factory=list)


@router.get("")
def list_runs(session: Session = Depends(get_db_session)) -> list[Any]:
    settings = get_settings()
    return TrackerRepository(session).list_runs(user_id=settings.user_id)


@router.post("")
def create_run(payload: RunInput, session: Session = Depends(get_db_session)) -> dict[str, Any]:
    settings = get_settings()
    allowed_sources = {"rss", "manual", "linkedin"}
    sources = [source for source in payload.sources if source in allowed_sources] or ["rss", "manual", "linkedin"]
    profile = get_effective_profile(TrackerRepository(session), settings.profile_path, settings.user_id)
    run_id = run_pipeline(profile=profile, sources=sources, limit=payload.limit, rss_urls=[payload.rss_feed], manual_urls=payload.manual_urls)
    run_row = session.get(RunTable, run_id)
    return {"run_id": run_id, "status": run_row.status if run_row else "completed", "jobs_collected": run_row.jobs_collected if run_row else 0}


@router.post("/{run_id}/resume")
def resume_run(run_id: str, session: Session = Depends(get_db_session)) -> dict[str, object]:
    settings = get_settings()
    repo = TrackerRepository(session)
    execution = repo.get_execution_run(run_id, user_id=settings.user_id)
    if execution is not None:
        return resume_execution(repo, settings, run_id, settings.user_id)
    run = repo.list_runs(user_id=settings.user_id)
    if not any(row.id == run_id for row in run):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")
    return {"run_id": run_id, "status": "resume_not_supported_for_intake_runs"}
