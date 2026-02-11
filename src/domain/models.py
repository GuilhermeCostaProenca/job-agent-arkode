from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field
from sqlmodel import SQLModel


class JobStatus(str, Enum):
    NEW = "new"
    REVIEWED = "reviewed"
    APPLIED = "applied"
    REJECTED = "rejected"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ExperienceItem(BaseModel):
    company: str
    period: str
    bullets: list[str]


class ProjectItem(BaseModel):
    name: str
    description: str
    stack: list[str]
    links: list[str] = Field(default_factory=list)


class CandidateProfile(BaseModel):
    name: str
    target_role: str
    location: str
    stacks: list[str]
    links: dict[str, str]
    experiences: list[ExperienceItem]
    projects: list[ProjectItem]
    education: list[str]
    preferences: dict[str, str | int | float | bool]


class JobPosting(BaseModel):
    external_id: str
    source: str
    url: str
    title: str
    company: str
    location: str
    description: str
    requirements: list[str] = Field(default_factory=list)
    posted_at: datetime | None = None
    score: int = 0
    score_reasons: list[str] = Field(default_factory=list)


class ScoringResult(BaseModel):
    score: int
    reasons: list[str]


class ArtifactBundle(BaseModel):
    resume_path: str
    cover_paths: list[str]
    dm_path: str
    email_path: str
    checklist_path: str


class RunSummary(BaseModel):
    run_id: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    jobs_collected: int
    jobs_scored: int


class DBJob(SQLModel):
    id: str
    run_id: str
    external_id: str
    source: str
    url: str
    title: str
    company: str
    location: str
    description: str
    score: int
    status: str = JobStatus.NEW.value


class DBRun(SQLModel):
    id: str
    started_at: datetime
    completed_at: datetime | None = None
    status: str = "running"
    jobs_collected: int = 0


class DBArtifact(SQLModel):
    id: str
    job_id: str
    run_id: str
    kind: str
    path: str


class DBApproval(SQLModel):
    id: str
    run_id: str
    job_id: str
    status: str = ApprovalStatus.PENDING.value
    reason: str
    payload: str
