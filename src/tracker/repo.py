from __future__ import annotations

import json
from datetime import UTC, date, datetime
from typing import Any, cast

from sqlmodel import Field, Session, SQLModel, select

from src.domain.models import ApplicationRecord, ApprovalStatus, ConfidenceLevel, ConnectorType, DBApproval, JobStatus


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
    connector: str = ConnectorType.GENERIC_EXTERNAL.value
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


class FeedItemTable(SQLModel, table=True):
    id: str = Field(primary_key=True)
    user_id: str = "default"
    source: str
    url: str
    text: str
    is_hiring: bool = False
    confidence: float = 0.0
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class CandidateProfileTable(SQLModel, table=True):
    id: str = Field(primary_key=True, default="default")
    user_id: str = "default"
    profile_json: str = "{}"
    updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class ProfileEvidenceTable(SQLModel, table=True):
    id: str = Field(primary_key=True)
    user_id: str = "default"
    kind: str
    title: str
    content: str
    source: str = "manual"
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class ProfileMemoryItemTable(SQLModel, table=True):
    id: str = Field(primary_key=True)
    user_id: str = "default"
    kind: str
    title: str
    content: str
    confidence: float = 0.5
    source: str = "derived"
    updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class ProfileConversationTurnTable(SQLModel, table=True):
    id: str = Field(primary_key=True)
    user_id: str = "default"
    role: str
    message: str
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class ApplicationArtifactSentTable(SQLModel, table=True):
    id: str = Field(primary_key=True)
    user_id: str = "default"
    application_id: str
    job_id: str
    kind: str
    label: str
    path: str
    content: str
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class ApplicationAnswerTable(SQLModel, table=True):
    id: str = Field(primary_key=True)
    user_id: str = "default"
    application_id: str
    job_id: str
    question: str
    answer: str
    confidence: str = ConfidenceLevel.MEDIUM.value
    rationale: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class ExecutionRunTable(SQLModel, table=True):
    id: str = Field(primary_key=True)
    user_id: str = "default"
    job_id: str
    application_id: str
    connector: str
    phase: str
    status: str
    trigger: str = "manual"
    current_step: str = "queued"
    error_message: str = ""
    pause_reason: str = ""
    retry_count: int = 0
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class ExecutionEventTable(SQLModel, table=True):
    id: str = Field(primary_key=True)
    user_id: str = "default"
    run_id: str
    step: str
    status: str
    message: str
    payload_json: str = "{}"
    screenshot_path: str = ""
    snapshot_path: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class EmailEventTable(SQLModel, table=True):
    id: str = Field(primary_key=True)
    user_id: str = "default"
    application_id: str
    provider: str
    external_id: str
    subject: str
    sender: str
    snippet: str
    status_inferred: str
    action_required: bool = False
    raw_json: str = "{}"
    received_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class BrowserSessionTable(SQLModel, table=True):
    id: str = Field(primary_key=True)
    user_id: str = "default"
    platform: str
    state: str
    profile_dir: str
    last_validated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    last_error: str = ""


class PlatformCredentialStateTable(SQLModel, table=True):
    id: str = Field(primary_key=True)
    user_id: str = "default"
    platform: str
    state: str
    detail: str = ""
    updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


APPLICATION_TO_JOB_STATUS: dict[str, str] = {
    "new": JobStatus.NEW.value,
    "prepared": JobStatus.NEW.value,
    "reviewed": JobStatus.REVIEWED.value,
    "approved": JobStatus.REVIEWED.value,
    "applied": JobStatus.APPLIED.value,
    "replied": JobStatus.APPLIED.value,
    "interview": JobStatus.APPLIED.value,
    "offer": JobStatus.APPLIED.value,
    "rejected": JobStatus.REJECTED.value,
}


class TrackerRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_run(self, run_id: str, user_id: str = "default") -> RunTable:
        row = RunTable(id=run_id, user_id=user_id)
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def finish_run(self, run_id: str, jobs_collected: int) -> RunTable | None:
        row = self.session.get(RunTable, run_id)
        if row is None:
            return None
        row.completed_at = datetime.now(UTC)
        row.jobs_collected = jobs_collected
        row.status = "completed"
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def upsert_job(self, **values: str | int) -> JobTable:
        job_id = str(values["id"])
        row = self.session.get(JobTable, job_id)
        if row is None:
            row = JobTable(**values)
        else:
            for key, value in values.items():
                setattr(row, key, value)
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def list_jobs(self, min_score: int = 0, status: str = JobStatus.NEW.value, limit: int = 20, user_id: str = "default") -> list[JobTable]:
        statement = select(JobTable).where(JobTable.user_id == user_id).where(JobTable.score >= min_score).where(JobTable.status == status).order_by(JobTable.score.desc()).limit(limit)  # type: ignore[attr-defined]
        return list(self.session.exec(statement))

    def list_jobs_all(self, min_score: int = 0, user_id: str = "default") -> list[JobTable]:
        statement = select(JobTable).where(JobTable.user_id == user_id).where(JobTable.score >= min_score).order_by(JobTable.score.desc())  # type: ignore[attr-defined]
        return list(self.session.exec(statement))

    def list_recommendations(self, min_score: int = 0, limit: int = 20, user_id: str = "default", explore: bool = False) -> list[dict[str, Any]]:
        jobs = self.list_jobs(min_score=min_score, limit=200, user_id=user_id)
        if not explore:
            return [{"job": row, "is_exploration": False} for row in jobs[:limit]]
        top_count = max(1, int(limit * 0.8))
        explore_count = max(1, limit - top_count)
        top_skills: list[str] = []
        top_locations: set[str] = set()
        for row in jobs[:top_count]:
            anchors = self.parse_json(row.anchors_json)
            top_skills.extend(anchors.get("top_skills", []))
            top_locations.add(row.location.lower())
        selected_rows = jobs[:top_count]
        selected = [{"job": row, "is_exploration": False} for row in selected_rows]
        top_skills_set = set(top_skills)
        known_companies = {row.company.lower() for row in selected_rows}
        exploration: list[dict[str, Any]] = []
        for row in jobs[top_count:]:
            anchors = self.parse_json(row.anchors_json)
            skills = set(anchors.get("top_skills", []))
            if row.score >= min_score and (bool(skills - top_skills_set) or row.location.lower() not in top_locations or row.company.lower() not in known_companies):
                exploration.append({"job": row, "is_exploration": True})
            if len(exploration) >= explore_count:
                break
        return (selected + exploration)[:limit]

    def get_job(self, job_id: str) -> JobTable | None:
        return self.session.get(JobTable, job_id)

    def get_job_by_external(self, source: str, external_id: str, user_id: str = "default") -> JobTable | None:
        statement = (
            select(JobTable)
            .where(JobTable.user_id == user_id)
            .where(JobTable.source == source)
            .where(JobTable.external_id == external_id)
        )
        return self.session.exec(statement).first()

    def list_runs(self, user_id: str = "default") -> list[RunTable]:
        statement = select(RunTable).where(RunTable.user_id == user_id).order_by(RunTable.started_at.desc())  # type: ignore[attr-defined]
        return list(self.session.exec(statement))

    def create_artifact(self, artifact_id: str, run_id: str, job_id: str, kind: str, path: str, user_id: str = "default") -> ArtifactTable:
        row = ArtifactTable(id=artifact_id, user_id=user_id, run_id=run_id, job_id=job_id, kind=kind, path=path)
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def list_artifacts(self, job_id: str, user_id: str = "default") -> list[ArtifactTable]:
        statement = select(ArtifactTable).where(ArtifactTable.job_id == job_id).where(ArtifactTable.user_id == user_id)
        return list(self.session.exec(statement))

    def find_artifact(self, job_id: str, artifact_name: str, user_id: str = "default") -> ArtifactTable | None:
        for row in self.list_artifacts(job_id, user_id=user_id):
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
        row = self.session.get(ApprovalTable, approval_id)
        if row is None:
            return None
        row.status = status
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def get_approval(self, approval_id: str) -> ApprovalTable | None:
        return self.session.get(ApprovalTable, approval_id)

    def upsert_application(self, record: ApplicationRecord, link: str, notes: str = "", user_id: str = "default", connector: str = ConnectorType.GENERIC_EXTERNAL.value) -> ApplicationTable:
        now = datetime.now(UTC).isoformat()
        row = self.session.get(ApplicationTable, record.id)
        if row is None:
            row = ApplicationTable(id=record.id, user_id=user_id, job_id=record.job_id, status=record.status, connector=connector, follow_up_date=record.follow_up_date, notes=notes, recommendation=record.recommendation, link=link, created_at=now, updated_at=now)
        else:
            row.status = record.status
            row.connector = connector or row.connector
            row.follow_up_date = record.follow_up_date
            row.recommendation = record.recommendation
            row.link = link
            row.notes = notes or row.notes
            row.updated_at = now
        self._sync_job_status(record.job_id, record.status, user_id=user_id)
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def update_application_status(self, job_id: str, status: str, notes: str = "", user_id: str = "default") -> ApplicationTable | None:
        statement = select(ApplicationTable).where(ApplicationTable.job_id == job_id).where(ApplicationTable.user_id == user_id)
        row = self.session.exec(statement).first()
        if row is None:
            return None
        row.status = status
        row.notes = notes or row.notes
        row.updated_at = datetime.now(UTC).isoformat()
        self._sync_job_status(job_id, status, user_id=user_id)
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def list_applications(self, status: str | None = None, user_id: str = "default") -> list[ApplicationTable]:
        statement = select(ApplicationTable).where(ApplicationTable.user_id == user_id)
        if status:
            statement = statement.where(ApplicationTable.status == status)
        statement = statement.order_by(ApplicationTable.updated_at.desc())  # type: ignore[attr-defined]
        return list(self.session.exec(statement))

    def get_application(self, application_id: str, user_id: str = "default") -> ApplicationTable | None:
        row = self.session.get(ApplicationTable, application_id)
        if row is None or row.user_id != user_id:
            return None
        return row

    def get_application_by_job(self, job_id: str, user_id: str = "default") -> ApplicationTable | None:
        statement = select(ApplicationTable).where(ApplicationTable.job_id == job_id).where(ApplicationTable.user_id == user_id)
        return self.session.exec(statement).first()

    def delete_job_bundle(self, job_id: str, user_id: str = "default") -> bool:
        job = self.get_job(job_id)
        if job is None or job.user_id != user_id:
            return False

        application = self.get_application_by_job(job_id, user_id=user_id)
        application_id = application.id if application is not None else None

        for row in self.list_artifacts(job_id, user_id=user_id):
            self.session.delete(row)
        for row in self.list_signals(user_id=user_id):
            if row.job_id == job_id:
                self.session.delete(row)
        statement = select(WritingDeltaTable).where(WritingDeltaTable.user_id == user_id).where(WritingDeltaTable.job_id == job_id)
        for row in self.session.exec(statement):
            self.session.delete(row)
        statement = select(ApprovalTable).where(ApprovalTable.user_id == user_id).where(ApprovalTable.job_id == job_id)
        for row in self.session.exec(statement):
            self.session.delete(row)

        execution_statement = select(ExecutionRunTable).where(ExecutionRunTable.user_id == user_id).where(ExecutionRunTable.job_id == job_id)
        execution_ids = [row.id for row in self.session.exec(execution_statement)]
        for execution_id in execution_ids:
            event_statement = select(ExecutionEventTable).where(ExecutionEventTable.user_id == user_id).where(ExecutionEventTable.run_id == execution_id)
            for event in self.session.exec(event_statement):
                self.session.delete(event)
            run = self.session.get(ExecutionRunTable, execution_id)
            if run is not None:
                self.session.delete(run)

        if application_id:
            for row in self.list_application_artifacts(application_id, user_id=user_id):
                self.session.delete(row)
            for row in self.list_application_answers(application_id, user_id=user_id):
                self.session.delete(row)
            email_statement = select(EmailEventTable).where(EmailEventTable.user_id == user_id).where(EmailEventTable.application_id == application_id)
            for row in self.session.exec(email_statement):
                self.session.delete(row)
            application = self.session.get(ApplicationTable, application_id)
            if application is not None:
                self.session.delete(application)

        self.session.delete(job)
        self.session.commit()
        return True

    def list_due_followups(self, until: date, user_id: str = "default") -> list[ApplicationTable]:
        follow_col = cast(Any, ApplicationTable.follow_up_date)
        statement = select(ApplicationTable).where(ApplicationTable.user_id == user_id).where(follow_col.is_not(None)).where(follow_col <= until).where(ApplicationTable.status != "rejected").order_by(follow_col.asc())
        return list(self.session.exec(statement))

    def create_signal(self, signal_id: str, run_id: str, job_id: str, signal_type: str, payload_json: dict[str, Any], created_at: str, user_id: str = "default") -> UserSignalTable:
        row = UserSignalTable(id=signal_id, run_id=run_id, job_id=job_id, signal_type=signal_type, payload_json=json.dumps(payload_json, ensure_ascii=False), created_at=created_at, user_id=user_id)
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def list_signals(self, limit: int = 50, user_id: str = "default") -> list[UserSignalTable]:
        statement = select(UserSignalTable).where(UserSignalTable.user_id == user_id).order_by(UserSignalTable.created_at.desc()).limit(limit)  # type: ignore[attr-defined]
        return list(self.session.exec(statement))

    def get_signals_after(self, signal_id: str, user_id: str = "default") -> list[UserSignalTable]:
        all_rows = self.list_signals(limit=5000, user_id=user_id)
        if not signal_id:
            return list(reversed(all_rows))
        found = False
        out: list[UserSignalTable] = []
        for row in reversed(all_rows):
            if found:
                out.append(row)
            if row.id == signal_id:
                found = True
        return out

    def create_writing_delta(self, delta_id: str, job_id: str, artifact_name: str, original_text: str, final_text: str, delta_json: dict[str, Any], user_id: str = "default") -> WritingDeltaTable:
        row = WritingDeltaTable(id=delta_id, user_id=user_id, job_id=job_id, artifact_name=artifact_name, original_text=original_text, final_text=final_text, delta_json=json.dumps(delta_json, ensure_ascii=False))
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def get_preference_model(self, user_id: str = "default") -> dict[str, Any] | None:
        statement = select(PreferenceModelTable).where(PreferenceModelTable.id == "default").where(PreferenceModelTable.user_id == user_id)
        row = self.session.exec(statement).first()
        return None if row is None else cast(dict[str, Any], json.loads(row.weights_json))

    def upsert_preference_model(self, model_id: str, weights: dict[str, Any], user_id: str = "default") -> PreferenceModelTable:
        statement = select(PreferenceModelTable).where(PreferenceModelTable.id == model_id).where(PreferenceModelTable.user_id == user_id)
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
        rows = list(self.session.exec(select(ApplicationTable.status).where(ApplicationTable.user_id == user_id)))
        summary: dict[str, int] = {}
        for status in rows:
            summary[status] = summary.get(status, 0) + 1
        return summary

    def create_feed_item(self, feed_id: str, source: str, url: str, text: str, is_hiring: bool, confidence: float, user_id: str = "default") -> FeedItemTable:
        row = FeedItemTable(id=feed_id, user_id=user_id, source=source, url=url, text=text, is_hiring=is_hiring, confidence=confidence)
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def list_feed_items(self, hiring_only: bool = False, user_id: str = "default") -> list[FeedItemTable]:
        statement = select(FeedItemTable).where(FeedItemTable.user_id == user_id)
        if hiring_only:
            statement = statement.where(cast(Any, FeedItemTable.is_hiring).is_(True))
        statement = statement.order_by(FeedItemTable.created_at.desc())  # type: ignore[attr-defined]
        return list(self.session.exec(statement))

    def get_feed_item(self, feed_id: str) -> FeedItemTable | None:
        return self.session.get(FeedItemTable, feed_id)

    def get_profile(self, user_id: str = "default") -> CandidateProfileTable | None:
        statement = select(CandidateProfileTable).where(CandidateProfileTable.id == "default").where(CandidateProfileTable.user_id == user_id)
        return self.session.exec(statement).first()

    def upsert_profile(self, profile_json: dict[str, Any], user_id: str = "default") -> CandidateProfileTable:
        row = self.get_profile(user_id=user_id)
        if row is None:
            row = CandidateProfileTable(id="default", user_id=user_id)
        row.profile_json = json.dumps(profile_json, ensure_ascii=False)
        row.updated_at = datetime.now(UTC).isoformat()
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def list_profile_evidence(self, user_id: str = "default") -> list[ProfileEvidenceTable]:
        statement = select(ProfileEvidenceTable).where(ProfileEvidenceTable.user_id == user_id).order_by(ProfileEvidenceTable.created_at.desc())  # type: ignore[attr-defined]
        return list(self.session.exec(statement))

    def clear_profile_evidence(self, user_id: str = "default") -> None:
        for row in self.list_profile_evidence(user_id=user_id):
            self.session.delete(row)
        self.session.commit()

    def create_profile_evidence(self, evidence_id: str, kind: str, title: str, content: str, source: str = "manual", user_id: str = "default") -> ProfileEvidenceTable:
        row = ProfileEvidenceTable(id=evidence_id, user_id=user_id, kind=kind, title=title, content=content, source=source)
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def list_profile_memory_items(self, user_id: str = "default") -> list[ProfileMemoryItemTable]:
        statement = select(ProfileMemoryItemTable).where(ProfileMemoryItemTable.user_id == user_id).order_by(ProfileMemoryItemTable.updated_at.desc())  # type: ignore[attr-defined]
        return list(self.session.exec(statement))

    def upsert_profile_memory_item(
        self,
        memory_id: str,
        kind: str,
        title: str,
        content: str,
        confidence: float = 0.5,
        source: str = "derived",
        user_id: str = "default",
    ) -> ProfileMemoryItemTable:
        row = self.session.get(ProfileMemoryItemTable, memory_id)
        if row is None:
            row = ProfileMemoryItemTable(id=memory_id, user_id=user_id, kind=kind, title=title, content=content, confidence=confidence, source=source)
        else:
            row.kind = kind
            row.title = title
            row.content = content
            row.confidence = confidence
            row.source = source
            row.updated_at = datetime.now(UTC).isoformat()
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def list_profile_conversation(self, limit: int = 100, user_id: str = "default") -> list[ProfileConversationTurnTable]:
        statement = select(ProfileConversationTurnTable).where(ProfileConversationTurnTable.user_id == user_id).order_by(ProfileConversationTurnTable.created_at.asc()).limit(limit)  # type: ignore[attr-defined]
        return list(self.session.exec(statement))

    def create_profile_conversation_turn(self, turn_id: str, role: str, message: str, user_id: str = "default") -> ProfileConversationTurnTable:
        row = ProfileConversationTurnTable(id=turn_id, user_id=user_id, role=role, message=message)
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def create_application_artifact(self, artifact_id: str, application_id: str, job_id: str, kind: str, label: str, path: str, content: str, user_id: str = "default") -> ApplicationArtifactSentTable:
        row = ApplicationArtifactSentTable(id=artifact_id, user_id=user_id, application_id=application_id, job_id=job_id, kind=kind, label=label, path=path, content=content)
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def list_application_artifacts(self, application_id: str, user_id: str = "default") -> list[ApplicationArtifactSentTable]:
        statement = select(ApplicationArtifactSentTable).where(ApplicationArtifactSentTable.application_id == application_id).where(ApplicationArtifactSentTable.user_id == user_id).order_by(ApplicationArtifactSentTable.created_at.asc())  # type: ignore[attr-defined]
        return list(self.session.exec(statement))

    def create_application_answer(self, answer_id: str, application_id: str, job_id: str, question: str, answer: str, confidence: str, rationale: str, user_id: str = "default") -> ApplicationAnswerTable:
        row = ApplicationAnswerTable(id=answer_id, user_id=user_id, application_id=application_id, job_id=job_id, question=question, answer=answer, confidence=confidence, rationale=rationale)
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def list_application_answers(self, application_id: str, user_id: str = "default") -> list[ApplicationAnswerTable]:
        statement = select(ApplicationAnswerTable).where(ApplicationAnswerTable.application_id == application_id).where(ApplicationAnswerTable.user_id == user_id).order_by(ApplicationAnswerTable.created_at.asc())  # type: ignore[attr-defined]
        return list(self.session.exec(statement))

    def create_execution_run(self, execution_id: str, application_id: str, job_id: str, connector: str, phase: str, status: str, trigger: str = "manual", user_id: str = "default") -> ExecutionRunTable:
        row = ExecutionRunTable(id=execution_id, user_id=user_id, application_id=application_id, job_id=job_id, connector=connector, phase=phase, status=status, trigger=trigger)
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def update_execution_run(
        self,
        execution_id: str,
        *,
        status: str | None = None,
        current_step: str | None = None,
        error_message: str | None = None,
        pause_reason: str | None = None,
        increment_retry: bool = False,
    ) -> ExecutionRunTable | None:
        row = self.session.get(ExecutionRunTable, execution_id)
        if row is None:
            return None
        if status is not None:
            row.status = status
        if current_step is not None:
            row.current_step = current_step
        if error_message is not None:
            row.error_message = error_message
        if pause_reason is not None:
            row.pause_reason = pause_reason
        if increment_retry:
            row.retry_count += 1
        row.updated_at = datetime.now(UTC).isoformat()
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def list_execution_runs(self, status: str | None = None, user_id: str = "default") -> list[ExecutionRunTable]:
        statement = select(ExecutionRunTable).where(ExecutionRunTable.user_id == user_id)
        if status:
            statement = statement.where(ExecutionRunTable.status == status)
        statement = statement.order_by(ExecutionRunTable.updated_at.desc())  # type: ignore[attr-defined]
        return list(self.session.exec(statement))

    def get_execution_run(self, execution_id: str, user_id: str = "default") -> ExecutionRunTable | None:
        row = self.session.get(ExecutionRunTable, execution_id)
        if row is None or row.user_id != user_id:
            return None
        return row

    def create_execution_event(self, event_id: str, run_id: str, step: str, status: str, message: str, payload: dict[str, Any], screenshot_path: str = "", snapshot_path: str = "", user_id: str = "default") -> ExecutionEventTable:
        row = ExecutionEventTable(id=event_id, user_id=user_id, run_id=run_id, step=step, status=status, message=message, payload_json=json.dumps(payload, ensure_ascii=False), screenshot_path=screenshot_path, snapshot_path=snapshot_path)
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def list_execution_events(self, run_id: str, user_id: str = "default") -> list[ExecutionEventTable]:
        statement = select(ExecutionEventTable).where(ExecutionEventTable.run_id == run_id).where(ExecutionEventTable.user_id == user_id).order_by(ExecutionEventTable.created_at.asc())  # type: ignore[attr-defined]
        return list(self.session.exec(statement))

    def create_email_event(self, event_id: str, application_id: str, provider: str, external_id: str, subject: str, sender: str, snippet: str, status_inferred: str, action_required: bool, raw_payload: dict[str, Any], user_id: str = "default") -> EmailEventTable:
        row = EmailEventTable(id=event_id, user_id=user_id, application_id=application_id, provider=provider, external_id=external_id, subject=subject, sender=sender, snippet=snippet, status_inferred=status_inferred, action_required=action_required, raw_json=json.dumps(raw_payload, ensure_ascii=False))
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def list_email_events(self, user_id: str = "default") -> list[EmailEventTable]:
        statement = select(EmailEventTable).where(EmailEventTable.user_id == user_id).order_by(EmailEventTable.received_at.desc())  # type: ignore[attr-defined]
        return list(self.session.exec(statement))

    def upsert_browser_session(self, session_id: str, platform: str, state: str, profile_dir: str, last_error: str = "", user_id: str = "default") -> BrowserSessionTable:
        row = self.session.get(BrowserSessionTable, session_id)
        if row is None:
            row = BrowserSessionTable(id=session_id, user_id=user_id, platform=platform, state=state, profile_dir=profile_dir, last_error=last_error)
        else:
            row.state = state
            row.profile_dir = profile_dir
            row.last_error = last_error
            row.last_validated_at = datetime.now(UTC).isoformat()
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def list_browser_sessions(self, user_id: str = "default") -> list[BrowserSessionTable]:
        statement = select(BrowserSessionTable).where(BrowserSessionTable.user_id == user_id).order_by(BrowserSessionTable.platform.asc())  # type: ignore[attr-defined]
        return list(self.session.exec(statement))

    def upsert_platform_credential_state(self, platform: str, state: str, detail: str = "", user_id: str = "default") -> PlatformCredentialStateTable:
        platform_id = f"{user_id}:{platform}"
        row = self.session.get(PlatformCredentialStateTable, platform_id)
        if row is None:
            row = PlatformCredentialStateTable(id=platform_id, user_id=user_id, platform=platform, state=state, detail=detail)
        else:
            row.state = state
            row.detail = detail
            row.updated_at = datetime.now(UTC).isoformat()
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def list_platform_credential_states(self, user_id: str = "default") -> list[PlatformCredentialStateTable]:
        statement = select(PlatformCredentialStateTable).where(PlatformCredentialStateTable.user_id == user_id).order_by(PlatformCredentialStateTable.platform.asc())  # type: ignore[attr-defined]
        return list(self.session.exec(statement))

    def dashboard_summary(self, user_id: str = "default") -> dict[str, Any]:
        jobs = self.list_jobs_all(min_score=0, user_id=user_id)
        applications = self.list_applications(user_id=user_id)
        runs = self.list_runs(user_id=user_id)
        execution_runs = self.list_execution_runs(user_id=user_id)
        email_events = self.list_email_events(user_id=user_id)
        platform_breakdown: dict[str, int] = {}
        for row in applications:
            platform_breakdown[row.connector] = platform_breakdown.get(row.connector, 0) + 1
        return {
            "jobs_discovered": len(jobs),
            "jobs_ready": len([row for row in jobs if row.recommendation == "APPLY"]),
            "applications_total": len(applications),
            "applications_submitted": len([row for row in applications if row.status in {"applied", "replied", "interview", "offer"}]),
            "execution_paused": len([row for row in execution_runs if row.status == "paused"]),
            "inbox_updates": len(email_events),
            "platform_breakdown": platform_breakdown,
            "recent_runs": [row.model_dump() for row in runs[:8]],
            "recent_executions": [row.model_dump() for row in execution_runs[:8]],
            "browser_sessions": [row.model_dump() for row in self.list_browser_sessions(user_id=user_id)],
            "credential_states": [row.model_dump() for row in self.list_platform_credential_states(user_id=user_id)],
        }

    @staticmethod
    def parse_json(value: str) -> dict[str, Any]:
        return cast(dict[str, Any], json.loads(value) if value else {})

    def _sync_job_status(self, job_id: str, application_status: str, user_id: str = "default") -> None:
        normalized = APPLICATION_TO_JOB_STATUS.get(application_status.strip().lower())
        if normalized is None:
            return
        job = self.session.get(JobTable, job_id)
        if job is None or job.user_id != user_id:
            return
        if job.status != normalized:
            job.status = normalized
            self.session.add(job)
            self.session.commit()
