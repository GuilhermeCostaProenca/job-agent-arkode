from pathlib import Path

from src.core.config import get_settings
from src.domain.models import CandidateProfile, ExperienceItem, JobPosting, ProjectItem
from src.domain.pipeline import run_pipeline
from src.tracker.db import get_session, init_db
from src.tracker.repo import TrackerRepository


def build_profile() -> CandidateProfile:
    return CandidateProfile(
        name="Ana",
        target_role="Júnior",
        location="remoto",
        stacks=["Flutter", "Kotlin", "SQL"],
        links={"github": "x"},
        experiences=[ExperienceItem(company="A", period="2023", bullets=["b"])],
        projects=[ProjectItem(name="P", description="d", stack=["Flutter"], links=[])],
        education=["ADS"],
        preferences={"company_type": "produto"},
    )


def test_pipeline_idempotency_for_same_job(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    get_settings.cache_clear()
    init_db()

    def fake_manual(url: str) -> JobPosting:
        return JobPosting(
            external_id="same-job",
            source="manual",
            url=url,
            title="Dev Mobile",
            company="Acme",
            location="remoto",
            description="Requisitos Flutter SQL",
        )

    monkeypatch.setattr("src.domain.pipeline.fetch_manual_url", fake_manual)

    profile = build_profile()
    run_pipeline(profile, ["manual"], 5, [], ["https://example.com/job"], artifacts_dir=tmp_path)
    run_pipeline(profile, ["manual"], 5, [], ["https://example.com/job"], artifacts_dir=tmp_path)

    with get_session() as session:
        rows = TrackerRepository(session).list_jobs_all()
    assert len(rows) == 1
