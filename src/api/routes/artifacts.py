from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session

from src.api.deps import get_db_session
from src.core.config import get_settings
from src.domain.signals import Signal, record_signal
from src.domain.writing_style import compute_writing_delta
from src.tracker.repo import TrackerRepository

router = APIRouter(prefix="/artifacts", tags=["artifacts"])


class EditedArtifactInput(BaseModel):
    artifact_name: str
    final_text: str


@router.get("/{job_id}")
def list_artifacts(job_id: str, session: Session = Depends(get_db_session)) -> list[Any]:
    settings = get_settings()
    return TrackerRepository(session).list_artifacts(job_id, user_id=settings.user_id)


@router.get("/{job_id}/content")
def get_artifact_content(job_id: str, kind: str, session: Session = Depends(get_db_session)) -> Any:
    settings = get_settings()
    repo = TrackerRepository(session)
    artifact = repo.find_artifact(job_id, kind, user_id=settings.user_id)
    if artifact is None:
        return {"detail": "artifact not found"}
    content = Path(artifact.path).read_text(encoding="utf-8")
    return {"kind": artifact.kind, "path": artifact.path, "content": content}


@router.post("/{job_id}/edited")
def artifact_edited(
    job_id: str,
    payload: EditedArtifactInput,
    session: Session = Depends(get_db_session),
) -> Any:
    settings = get_settings()
    repo = TrackerRepository(session)
    artifact = repo.find_artifact(job_id, payload.artifact_name, user_id=settings.user_id)
    if artifact is None:
        return {"detail": "artifact not found"}
    original_text = Path(artifact.path).read_text(encoding="utf-8")
    delta = compute_writing_delta(original_text, payload.final_text)
    row = repo.create_writing_delta(
        delta_id=str(uuid4()),
        job_id=job_id,
        artifact_name=payload.artifact_name,
        original_text=original_text,
        final_text=payload.final_text,
        delta_json=delta,
        user_id=settings.user_id,
    )
    record_signal(
        repo,
        Signal(
            signal_type="artifact_edit",
            job_id=job_id,
            payload={"artifact_name": payload.artifact_name, "delta": delta},
            user_id=settings.user_id,
            run_id="api",
        ),
    )
    return row
