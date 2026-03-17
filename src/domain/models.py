from __future__ import annotations

from datetime import UTC, date, datetime
from enum import Enum
from typing import Any

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


class ConnectorType(str, Enum):
    LINKEDIN = "linkedin"
    GUPY = "gupy"
    GREENHOUSE = "greenhouse"
    LEVER = "lever"
    GENERIC_EXTERNAL = "generic_external"


class ExecutionStatus(str, Enum):
    QUEUED = "queued"
    PREPARING = "preparing"
    APPLYING = "applying"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


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
    bullet_bank: dict[str, list[str]] = Field(default_factory=dict)
    learning_plan: list[str] = Field(default_factory=list)


class ProfileEvidence(BaseModel):
    id: str
    kind: str
    title: str
    content: str
    source: str = "manual"
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class ProfileSnapshot(BaseModel):
    profile: CandidateProfile
    evidences: list[ProfileEvidence] = Field(default_factory=list)


class ProfileMemoryItem(BaseModel):
    id: str
    kind: str
    title: str
    content: str
    confidence: float = 0.5
    source: str = "derived"
    updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class ProfileConversationTurn(BaseModel):
    id: str
    role: str
    message: str
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class ProfileConflict(BaseModel):
    id: str
    field: str
    summary: str
    recommended_action: str
    values: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    confidence: float = 0.5


class ProfileBrainSnapshot(BaseModel):
    profile: CandidateProfile
    evidences: list[ProfileEvidence] = Field(default_factory=list)
    memory_items: list[ProfileMemoryItem] = Field(default_factory=list)
    conversation: list[ProfileConversationTurn] = Field(default_factory=list)
    conflicts: list[ProfileConflict] = Field(default_factory=list)


class JobAnchors(BaseModel):
    top_skills: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    soft_keywords: list[str] = Field(default_factory=list)
    must_have: list[str] = Field(default_factory=list)
    nice_to_have: list[str] = Field(default_factory=list)
    mission_keywords: list[str] = Field(default_factory=list)


class ScoreBreakdown(BaseModel):
    skill_match_score: int
    seniority_score: int
    location_score: int
    keyword_density_score: int
    red_flag_penalty: int


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
    anchors: JobAnchors = Field(default_factory=JobAnchors)
    score_breakdown: ScoreBreakdown | None = None


class ScoringResult(BaseModel):
    score: int
    reasons: list[str]
    breakdown: ScoreBreakdown
    top_matched_terms: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    preference_adjustments: dict[str, float] = Field(default_factory=dict)
    fit_summary: str = ""
    recommendation: str = "MAYBE"
    llm_adjustment: int = 0


class ArtifactBundle(BaseModel):
    resume_path: str
    cover_paths: list[str]
    dm_path: str
    email_path: str
    checklist_path: str
    match_analysis_path: str
    project_prompt_path: str


class GeneratedAnswer(BaseModel):
    question: str
    answer: str
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    rationale: str = ""


class ApplicationArtifactRecord(BaseModel):
    kind: str
    label: str
    path: str
    content: str


class ExecutionCheckpoint(BaseModel):
    step: str
    status: str
    message: str
    screenshot_path: str | None = None
    snapshot_path: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class DashboardSnapshot(BaseModel):
    jobs_discovered: int = 0
    jobs_ready: int = 0
    applications_total: int = 0
    applications_submitted: int = 0
    execution_paused: int = 0
    inbox_updates: int = 0
    platform_breakdown: dict[str, int] = Field(default_factory=dict)


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


class ApplicationRecord(SQLModel):
    id: str
    job_id: str
    status: str = "new"
    follow_up_date: date | None = None
    recommendation: str = "MAYBE"
