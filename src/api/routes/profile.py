from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import Session

from src.api.deps import get_db_session
from src.core.config import get_settings
from src.domain.models import CandidateProfile, ProfileBrainSnapshot, ProfileEvidence, ProfileSnapshot
from src.services.github_profile_service import import_github_profile
from src.services.linkedin_profile_service import import_linkedin_profile
from src.services.profile_brain_service import chat_with_profile_brain, get_profile_brain, resolve_profile_conflict
from src.services.profile_service import get_profile_snapshot, save_profile_snapshot
from src.tracker.repo import TrackerRepository

router = APIRouter(prefix="/profile", tags=["profile"])


class ProfileEvidenceInput(BaseModel):
    id: str = ""
    kind: str
    title: str
    content: str
    source: str = "manual"


class ProfileSnapshotInput(BaseModel):
    profile: CandidateProfile
    evidences: list[ProfileEvidenceInput] = Field(default_factory=list)


class ProfileChatInput(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class ProfileChatResponse(BaseModel):
    assistant_message: str
    brain: ProfileBrainSnapshot


class GitHubImportInput(BaseModel):
    github_url: str | None = None


class GitHubImportResponse(BaseModel):
    assistant_message: str
    brain: ProfileBrainSnapshot
    imported_repositories: int
    github_username: str


class LinkedInImportInput(BaseModel):
    linkedin_url: str | None = None


class LinkedInImportResponse(BaseModel):
    assistant_message: str
    brain: ProfileBrainSnapshot
    linkedin_url: str


class ProfileConflictResolutionInput(BaseModel):
    field: str = Field(min_length=1)
    chosen_value: str = Field(min_length=1)


@router.get("")
def get_profile(session: Session = Depends(get_db_session)) -> ProfileSnapshot:
    settings = get_settings()
    return get_profile_snapshot(TrackerRepository(session), settings.profile_path, settings.user_id)


@router.put("")
def update_profile(payload: ProfileSnapshotInput, session: Session = Depends(get_db_session)) -> ProfileSnapshot:
    settings = get_settings()
    snapshot = ProfileSnapshot(profile=payload.profile, evidences=[ProfileEvidence(**item.model_dump()) for item in payload.evidences])
    return save_profile_snapshot(TrackerRepository(session), snapshot, settings.user_id)


@router.get("/brain")
def get_profile_brain_snapshot(session: Session = Depends(get_db_session)) -> ProfileBrainSnapshot:
    settings = get_settings()
    return get_profile_brain(TrackerRepository(session), settings.profile_path, settings.user_id)


@router.post("/chat")
def post_profile_chat(payload: ProfileChatInput, session: Session = Depends(get_db_session)) -> ProfileChatResponse:
    settings = get_settings()
    result = chat_with_profile_brain(TrackerRepository(session), settings, payload.message, settings.user_id)
    return ProfileChatResponse(assistant_message=str(result["assistant_message"]), brain=ProfileBrainSnapshot.model_validate(result["brain"]))


@router.post("/import/github")
def post_import_github_profile(payload: GitHubImportInput, session: Session = Depends(get_db_session)) -> GitHubImportResponse:
    settings = get_settings()
    try:
        result = import_github_profile(
            TrackerRepository(session),
            settings,
            settings.user_id,
            github_url=payload.github_url,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return GitHubImportResponse(
        assistant_message=str(result["assistant_message"]),
        brain=ProfileBrainSnapshot.model_validate(result["brain"]),
        imported_repositories=int(result["imported_repositories"]),
        github_username=str(result["github_username"]),
    )


@router.post("/import/linkedin")
def post_import_linkedin_profile(payload: LinkedInImportInput, session: Session = Depends(get_db_session)) -> LinkedInImportResponse:
    settings = get_settings()
    try:
        result = import_linkedin_profile(
            TrackerRepository(session),
            settings,
            settings.user_id,
            linkedin_url=payload.linkedin_url,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return LinkedInImportResponse(
        assistant_message=str(result["assistant_message"]),
        brain=ProfileBrainSnapshot.model_validate(result["brain"]),
        linkedin_url=str(result["linkedin_url"]),
    )


@router.post("/conflicts/resolve")
def post_resolve_profile_conflict(payload: ProfileConflictResolutionInput, session: Session = Depends(get_db_session)) -> ProfileChatResponse:
    settings = get_settings()
    try:
        result = resolve_profile_conflict(
            TrackerRepository(session),
            settings,
            settings.user_id,
            field=payload.field,
            chosen_value=payload.chosen_value,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return ProfileChatResponse(
        assistant_message=str(result["assistant_message"]),
        brain=ProfileBrainSnapshot.model_validate(result["brain"]),
    )
