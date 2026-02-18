from src.domain.models import DBApproval
from src.tracker.repo import TrackerRepository


def create_approval(
    repo: TrackerRepository,
    run_id: str,
    job_id: str,
    reason: str,
    payload: str,
) -> DBApproval:
    approval = DBApproval(
        id=f"approval-{run_id}-{job_id}",
        run_id=run_id,
        job_id=job_id,
        reason=reason,
        payload=payload,
    )
    repo.create_approval(approval)
    return approval


def decide_approval(repo: TrackerRepository, approval_id: str, approve: bool) -> DBApproval | None:
    status = "approved" if approve else "rejected"
    row = repo.update_approval_status(approval_id, status)
    if row is None:
        return None
    return DBApproval.model_validate(row.model_dump())
