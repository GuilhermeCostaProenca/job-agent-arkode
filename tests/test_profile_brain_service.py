from pathlib import Path

from src.core.config import get_settings
from src.domain.models import CandidateProfile, ExperienceItem, JobPosting, ProjectItem
from src.domain.scoring import score_job
from src.services.profile_brain_service import get_effective_profile, resolve_profile_conflict
from src.tracker.db import get_session, init_db
from src.tracker.repo import TrackerRepository


def _setup(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "agent.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("USER_ID", "default")
    get_settings.cache_clear()
    init_db()


def _profile() -> CandidateProfile:
    return CandidateProfile(
        name="Ana",
        target_role="Pleno",
        location="Sao Paulo presencial",
        stacks=["React", "Node.js"],
        links={"github": "https://github.com/ana"},
        experiences=[ExperienceItem(company="Acme", period="2025", bullets=["Built internal tools"])],
        projects=[ProjectItem(name="Portal", description="Internal platform", stack=["React"], links=[])],
        education=["ADS"],
        preferences={},
        bullet_bank={},
        learning_plan=[],
    )


def test_effective_profile_applies_user_confirmations(monkeypatch, tmp_path: Path) -> None:
    _setup(monkeypatch, tmp_path)
    settings = get_settings()

    with get_session() as session:
        repo = TrackerRepository(session)
        repo.upsert_profile(_profile().model_dump(), user_id=settings.user_id)
        resolve_profile_conflict(repo, settings, settings.user_id, field="target_role", chosen_value="Junior")
        resolve_profile_conflict(repo, settings, settings.user_id, field="stacks", chosen_value="Python, FastAPI, SQL")
        effective = get_effective_profile(repo, settings.profile_path, settings.user_id)

    assert effective.target_role == "Junior"
    assert effective.stacks == ["Python", "FastAPI", "SQL"]


def test_score_job_uses_effective_profile_after_confirmation(monkeypatch, tmp_path: Path) -> None:
    _setup(monkeypatch, tmp_path)
    settings = get_settings()
    job = JobPosting(
        external_id="1",
        source="manual",
        url="https://example.com/job",
        title="Backend Engineer Junior",
        company="Beta",
        location="remoto",
        description="Need Python FastAPI SQL",
        requirements=["Python", "FastAPI", "SQL"],
    )

    with get_session() as session:
        repo = TrackerRepository(session)
        repo.upsert_profile(_profile().model_dump(), user_id=settings.user_id)
        baseline = score_job(job, _profile())
        resolve_profile_conflict(repo, settings, settings.user_id, field="target_role", chosen_value="Junior")
        resolve_profile_conflict(repo, settings, settings.user_id, field="location", chosen_value="remoto")
        resolve_profile_conflict(repo, settings, settings.user_id, field="stacks", chosen_value="Python, FastAPI, SQL")
        effective = get_effective_profile(repo, settings.profile_path, settings.user_id)
        resolved = score_job(job, effective)

    assert baseline.score < resolved.score
    assert resolved.recommendation in {"APPLY", "MAYBE"}
