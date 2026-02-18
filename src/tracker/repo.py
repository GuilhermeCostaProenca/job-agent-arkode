from __future__ import annotations

import json
from datetime import UTC, date, datetime
from typing import Any, cast

from sqlmodel import Field, Session, SQLModel, select

from src.domain.models import ApplicationRecord, ApprovalStatus, DBApproval, JobStatus


class JobTable(SQLModel, table=True):
    id: str = Field(primary_key=True)
    user_id: str = "default"
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
    anchors_json: str = "{}"
    score_breakdown_json: str = "{}"
    recommendation: str = "MAYBE"
    status: str = JobStatus.NEW.value


class RunTable(SQLModel, table=True):
    id: str = Field(primary_key=True)
    user_id: str = "default"
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    status: str = "running"
    jobs_collected: int = 0


class ArtifactTable(SQLModel, table=True):
    id: str = Field(primary_key=True)
    user_id: str = "default"
    run_id: str
    job_id: str
    kind: str
    path: str


class ApprovalTable(SQLModel, table=True):
    id: str = Field(primary_key=True)
    user_id: str = "default"
    run_id: str
    job_id: str
    status: str = ApprovalStatus.PENDING.value
    reason: str
    payload: str


class ApplicationTable(SQLModel, table=True):
    id: str = Field(primary_key=True)
    user_id: str = "default"
    job_id: str
    status: str = "new"
    follow_up_date: date | None = None
    notes: str = ""
    recommendation: str = "MAYBE"
    link: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class UserSignalTable(SQLModel, table=True):
    id: str = Field(primary_key=True)
    user_id: str = "default"
    run_id: str
    job_id: str
    signal_type: str
    payload_json: str = "{}"
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class PreferenceModelTable(SQLModel, table=True):
    id: str = Field(primary_key=True, default="default")
    user_id: str = "default"
    weights_json: str = "{}"
    updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class WritingDeltaTable(SQLModel, table=True):
    id: str = Field(primary_key=True)
    user_id: str = "default"
    job_id: str
    artifact_name: str
    original_text: str
    final_text: str
    delta_json: str
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class TrackerRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_run(self, run_id: str, user_id: str = "default") -> RunTable:
        run = RunTable(id=run_id, user_id=user_id)
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
        user_id: str = "default",
    ) -> list[JobTable]:
        statement = (
            select(JobTable)
            .where(JobTable.user_id == user_id)
            .where(JobTable.score >= min_score)
            .where(JobTable.status == status)
            .order_by(JobTable.score.desc())  # type: ignore[attr-defined]
            .limit(limit)
        )
        return list(self.session.exec(statement))

    def list_jobs_all(self, min_score: int = 0, user_id: str = "default") -> list[JobTable]:
        statement = (
            select(JobTable)
            .where(JobTable.user_id == user_id)
            .where(JobTable.score >= min_score)
            .order_by(JobTable.score.desc())  # type: ignore[attr-defined]
        )
        return list(self.session.exec(statement))

    def get_job(self, job_id: str) -> JobTable | None:
        return self.session.get(JobTable, job_id)

    def list_runs(self, user_id: str = "default") -> list[RunTable]:
        statement = (
            select(RunTable).where(RunTable.user_id == user_id).order_by(RunTable.started_at.desc())  # type: ignore[attr-defined]
        )
        return list(self.session.exec(statement))

    def create_artifact(
        self,
        artifact_id: str,
        run_id: str,
        job_id: str,
        kind: str,
        path: str,
        user_id: str = "default",
    ) -> ArtifactTable:
        artifact = ArtifactTable(
            id=artifact_id,
            user_id=user_id,
            run_id=run_id,
            job_id=job_id,
            kind=kind,
            path=path,
        )
        self.session.add(artifact)
        self.session.commit()
        self.session.refresh(artifact)
        return artifact

    def list_artifacts(self, job_id: str, user_id: str = "default") -> list[ArtifactTable]:
        statement = (
            select(ArtifactTable)
            .where(ArtifactTable.job_id == job_id)
            .where(ArtifactTable.user_id == user_id)
        )
        return list(self.session.exec(statement))

    def find_artifact(
        self, job_id: str, artifact_name: str, user_id: str = "default"
    ) -> ArtifactTable | None:
        rows = self.list_artifacts(job_id, user_id=user_id)
        for row in rows:
            if artifact_name in row.kind or artifact_name in row.path:
                return row
        return None

    def create_approval(self, approval: DBApproval, user_id: str = "default") -> ApprovalTable:
        row = ApprovalTable(**approval.model_dump(), user_id=user_id)
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

    def upsert_application(
        self,
        record: ApplicationRecord,
        link: str,
        notes: str = "",
        user_id: str = "default",
    ) -> ApplicationTable:
        row = self.session.get(ApplicationTable, record.id)
        now = datetime.now(UTC).isoformat()
        if row is None:
            row = ApplicationTable(
                id=record.id,
                user_id=user_id,
                job_id=record.job_id,
                status=record.status,
                follow_up_date=record.follow_up_date,
                notes=notes,
                recommendation=record.recommendation,
                link=link,
                created_at=now,
                updated_at=now,
            )
        else:
            row.status = record.status
            row.follow_up_date = record.follow_up_date
            row.recommendation = record.recommendation
            row.link = link
            row.notes = notes or row.notes
            row.updated_at = now
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def update_application_status(
        self,
        job_id: str,
        status: str,
        notes: str = "",
        user_id: str = "default",
    ) -> ApplicationTable | None:
        statement = (
            select(ApplicationTable)
            .where(ApplicationTable.job_id == job_id)
            .where(ApplicationTable.user_id == user_id)
        )
        row = self.session.exec(statement).first()
        if row is None:
            return None
        row.status = status
        row.notes = notes or row.notes
        row.updated_at = datetime.now(UTC).isoformat()
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def list_due_followups(self, until: date, user_id: str = "default") -> list[ApplicationTable]:
        follow_col = cast(Any, ApplicationTable.follow_up_date)
        statement = (
            select(ApplicationTable)
            .where(ApplicationTable.user_id == user_id)
            .where(follow_col.is_not(None))
            .where(follow_col <= until)
            .where(ApplicationTable.status != "rejected")
            .order_by(follow_col.asc())
        )
        return list(self.session.exec(statement))

    def create_signal(
        self,
        signal_id: str,
        run_id: str,
        job_id: str,
        signal_type: str,
        payload_json: dict[str, Any],
        created_at: str,
        user_id: str = "default",
    ) -> UserSignalTable:
        row = UserSignalTable(
            id=signal_id,
            run_id=run_id,
            job_id=job_id,
            signal_type=signal_type,
            payload_json=json.dumps(payload_json, ensure_ascii=False),
            created_at=created_at,
            user_id=user_id,
        )
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def list_signals(self, limit: int = 50, user_id: str = "default") -> list[UserSignalTable]:
        statement = (
            select(UserSignalTable)
            .where(UserSignalTable.user_id == user_id)
            .order_by(UserSignalTable.created_at.desc())  # type: ignore[attr-defined]
            .limit(limit)
        )
        return list(self.session.exec(statement))

    def get_signals_after(self, signal_id: str, user_id: str = "default") -> list[UserSignalTable]:
        all_rows = self.list_signals(limit=5000, user_id=user_id)
        if not signal_id:
            return list(reversed(all_rows))
        out: list[UserSignalTable] = []
        found = False
        for row in reversed(all_rows):
            if found:
                out.append(row)
            if row.id == signal_id:
                found = True
        return out

    def create_writing_delta(
        self,
        delta_id: str,
        job_id: str,
        artifact_name: str,
        original_text: str,
        final_text: str,
        delta_json: dict[str, Any],
        user_id: str = "default",
    ) -> WritingDeltaTable:
        row = WritingDeltaTable(
            id=delta_id,
            user_id=user_id,
            job_id=job_id,
            artifact_name=artifact_name,
            original_text=original_text,
            final_text=final_text,
            delta_json=json.dumps(delta_json, ensure_ascii=False),
        )
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def get_preference_model(self, user_id: str = "default") -> dict[str, Any] | None:
        statement = (
            select(PreferenceModelTable)
            .where(PreferenceModelTable.id == "default")
            .where(PreferenceModelTable.user_id == user_id)
        )
        row = self.session.exec(statement).first()
        if row is None:
            return None
        data = json.loads(row.weights_json)
        return cast(dict[str, Any], data)

    def upsert_preference_model(
        self,
        model_id: str,
        weights: dict[str, Any],
        user_id: str = "default",
    ) -> PreferenceModelTable:
        statement = (
            select(PreferenceModelTable)
            .where(PreferenceModelTable.id == model_id)
            .where(PreferenceModelTable.user_id == user_id)
        )
        row = self.session.exec(statement).first()
        if row is None:
            row = PreferenceModelTable(id=model_id, user_id=user_id)
        row.weights_json = json.dumps(weights, ensure_ascii=False)
        row.updated_at = datetime.now(UTC).isoformat()
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def summarize_applications(self, user_id: str = "default") -> dict[str, int]:
        rows = list(
            self.session.exec(
                select(ApplicationTable.status).where(ApplicationTable.user_id == user_id)
            )
        )
        summary: dict[str, int] = {}
        for status in rows:
            summary[status] = summary.get(status, 0) + 1
        return summary

    @staticmethod
    def parse_json(value: str) -> dict[str, object]:
        return json.loads(value) if value else {}
