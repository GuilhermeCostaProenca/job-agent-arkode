from typing import Any

from fastapi import APIRouter, Depends
from sqlmodel import Session

from src.api.deps import get_db_session
from src.tracker.repo import TrackerRepository

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.post("/{approval_id}/approve")
def approve(approval_id: str, session: Session = Depends(get_db_session)) -> Any:
    updated = TrackerRepository(session).update_approval_status(approval_id, "approved")
    return updated or {"detail": "approval not found"}


@router.post("/{approval_id}/reject")
def reject(approval_id: str, session: Session = Depends(get_db_session)) -> Any:
    updated = TrackerRepository(session).update_approval_status(approval_id, "rejected")
    return updated or {"detail": "approval not found"}
