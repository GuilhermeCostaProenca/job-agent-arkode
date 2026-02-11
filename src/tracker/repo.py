from __future__ import annotations

from datetime import UTC, datetime

from sqlmodel import Field, Session, SQLModel, select

from src.domain.models import ApprovalStatus, DBApproval, JobStatus


class JobTable(SQLModel, table=True):
    id: str = Field(primary_key=True)
    run_id: str
    external_id: str
    source: str
    url: str
    title: str
    company: str
    location: str
    description: str
    score: int = 0
    score_reasons: str = ""
    status: str = JobStatus.NEW.value


class RunTable(SQLModel, table=True):
    id: str = Field(primary_key=True)
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    status: str = "running"
    jobs_collected: int = 0


class ArtifactTable(SQLModel, table=True):
    id: str = Field(primary_key=True)
    run_id: str
    job_id: str
    kind: str
    path: str


class ApprovalTable(SQLModel, table=True):
    id: str = Field(primary_key=True)
    run_id: str
    job_id: str
    status: str = ApprovalStatus.PENDING.value
    reason: str
    payload: str


class TrackerRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_run(self, run_id: str) -> RunTable:
        run = RunTable(id=run_id)
        self.session.add(run)
        self.session.commit()
        self.session.refresh(run)
        return run

    def finish_run(self, run_id: str, jobs_collected: int) -> RunTable | None:
        run = self.session.get(RunTable, run_id)
        if run is None:
            return None
        run.completed_at = datetime.now(UTC)
        run.jobs_collected = jobs_collected
        run.status = "completed"
        self.session.add(run)
        self.session.commit()
        self.session.refresh(run)
        return run

    def upsert_job(self, **values: str | int) -> JobTable:
        job_id = str(values["id"])
        job = self.session.get(JobTable, job_id)
        if job is None:
            job = JobTable(**values)
        else:
            for key, value in values.items():
                setattr(job, key, value)
        self.session.add(job)
        self.session.commit()
        self.session.refresh(job)
        return job

    def list_jobs(
        self,
        min_score: int = 0,
        status: str = JobStatus.NEW.value,
        limit: int = 20,
    ) -> list[JobTable]:
        statement = (
            select(JobTable)
            .where(JobTable.score >= min_score)
            .where(JobTable.status == status)
            .order_by(JobTable.score.desc())  # type: ignore[attr-defined]
            .limit(limit)
        )
        return list(self.session.exec(statement))

    def get_job(self, job_id: str) -> JobTable | None:
        return self.session.get(JobTable, job_id)

    def list_runs(self) -> list[RunTable]:
        statement = select(RunTable).order_by(RunTable.started_at.desc())  # type: ignore[attr-defined]
        return list(self.session.exec(statement))

    def create_artifact(
        self,
        artifact_id: str,
        run_id: str,
        job_id: str,
        kind: str,
        path: str,
    ) -> ArtifactTable:
        artifact = ArtifactTable(id=artifact_id, run_id=run_id, job_id=job_id, kind=kind, path=path)
        self.session.add(artifact)
        self.session.commit()
        self.session.refresh(artifact)
        return artifact

    def list_artifacts(self, job_id: str) -> list[ArtifactTable]:
        return list(self.session.exec(select(ArtifactTable).where(ArtifactTable.job_id == job_id)))

    def create_approval(self, approval: DBApproval) -> ApprovalTable:
        row = ApprovalTable(**approval.model_dump())
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def update_approval_status(self, approval_id: str, status: str) -> ApprovalTable | None:
        approval = self.session.get(ApprovalTable, approval_id)
        if approval is None:
            return None
        approval.status = status
        self.session.add(approval)
        self.session.commit()
        self.session.refresh(approval)
        return approval

    def get_approval(self, approval_id: str) -> ApprovalTable | None:
        return self.session.get(ApprovalTable, approval_id)
