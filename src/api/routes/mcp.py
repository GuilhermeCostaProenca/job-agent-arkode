from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.core.config import get_settings
from src.domain.pipeline import run_pipeline
from src.services.github_profile_service import import_github_profile
from src.services.linkedin_diagnostic_service import run_linkedin_diagnostic, run_linkedin_discovery_preview, run_linkedin_session_setup
from src.services.linkedin_profile_service import import_linkedin_profile
from src.services.linkedin_purge_service import purge_low_fit_linkedin_jobs
from src.services.linkedin_repair_service import repair_linkedin_jobs
from src.services.profile_brain_service import get_effective_profile
from src.tracker.db import get_session
from src.tracker.repo import RunTable, TrackerRepository
from src.services.mcp_service import list_tools

router = APIRouter(prefix="/mcp", tags=["mcp"])


class GitHubImportInput(BaseModel):
    github_url: str | None = None


class LinkedInImportInput(BaseModel):
    linkedin_url: str | None = None


class JobDiscoveryInput(BaseModel):
    sources: list[str] = Field(default_factory=lambda: ["rss", "manual", "linkedin"])
    limit: int = Field(default=30, ge=1, le=200)
    rss_feed: str = "https://remoteok.com/remote-dev-jobs.rss"
    manual_urls: list[str] = Field(default_factory=list)


@router.get("/tools")
def get_tools() -> list[dict[str, str]]:
    return list_tools()


@router.post("/linkedin/diagnose")
def diagnose_linkedin_job(job_url: str = Query(..., alias="job_url")) -> dict[str, object]:
    settings = get_settings()
    if "linkedin.com" not in job_url:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="job_url must be a LinkedIn job URL")
    with get_session() as session:
        return run_linkedin_diagnostic(TrackerRepository(session), settings, job_url)


@router.post("/linkedin/session/setup")
def setup_linkedin_session() -> dict[str, object]:
    settings = get_settings()
    with get_session() as session:
        return run_linkedin_session_setup(TrackerRepository(session), settings)


@router.post("/linkedin/discover")
def discover_linkedin_jobs(limit: int = Query(default=10, ge=1, le=30)) -> dict[str, object]:
    settings = get_settings()
    with get_session() as session:
        return run_linkedin_discovery_preview(TrackerRepository(session), settings, limit=limit)


@router.post("/linkedin/repair")
def repair_linkedin_job_records(limit: int = Query(default=10, ge=1, le=30)) -> dict[str, object]:
    settings = get_settings()
    with get_session() as session:
        return repair_linkedin_jobs(TrackerRepository(session), settings, limit=limit)


@router.post("/linkedin/purge")
def purge_linkedin_job_records(limit: int = Query(default=20, ge=1, le=100)) -> dict[str, object]:
    settings = get_settings()
    with get_session() as session:
        return purge_low_fit_linkedin_jobs(TrackerRepository(session), settings.user_id, limit=limit)


@router.post("/profile/github/import")
def import_github_profile_tool(payload: GitHubImportInput) -> dict[str, object]:
    settings = get_settings()
    with get_session() as session:
        try:
            return import_github_profile(TrackerRepository(session), settings, settings.user_id, github_url=payload.github_url)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/profile/linkedin/import")
def import_linkedin_profile_tool(payload: LinkedInImportInput) -> dict[str, object]:
    settings = get_settings()
    with get_session() as session:
        try:
            return import_linkedin_profile(TrackerRepository(session), settings, settings.user_id, linkedin_url=payload.linkedin_url)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/jobs/discover")
def discover_jobs_tool(payload: JobDiscoveryInput) -> dict[str, object]:
    settings = get_settings()
    allowed_sources = {"rss", "manual", "linkedin"}
    sources = [source for source in payload.sources if source in allowed_sources] or ["rss", "manual", "linkedin"]
    with get_session() as session:
        repo = TrackerRepository(session)
        effective_profile = get_effective_profile(repo, settings.profile_path, settings.user_id)
        run_id = run_pipeline(
            profile=effective_profile,
            sources=sources,
            limit=payload.limit,
            rss_urls=[payload.rss_feed],
            manual_urls=payload.manual_urls,
        )
        run_row = session.get(RunTable, run_id)
    return {
        "run_id": run_id,
        "status": run_row.status if run_row else "completed",
        "jobs_collected": run_row.jobs_collected if run_row else 0,
        "effective_profile": {
            "target_role": effective_profile.target_role,
            "location": effective_profile.location,
            "stacks": effective_profile.stacks,
        },
    }
