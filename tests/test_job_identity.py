from pathlib import Path

from src.core.config import get_settings
from src.core.ids import generate_job_id
from src.domain.models import ApplicationRecord, CandidateProfile, JobPosting
from src.domain.pipeline import run_pipeline
from src.tracker.db import get_session, init_db
from src.tracker.repo import TrackerRepository


def _setup(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "agent.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("USER_ID", "default")
    get_settings.cache_clear()
    init_db()


def test_generate_job_id_is_stable_for_same_external_id() -> None:
    first = generate_job_id("linkedin", "https://www.linkedin.com/jobs/view/123", "Acme", "Backend Engineer")
    second = generate_job_id("linkedin", "https://www.linkedin.com/jobs/view/123", "Acme Updated", "Senior Backend Engineer")

    assert first == second


def test_pipeline_updates_existing_job_for_same_external_id(monkeypatch, tmp_path: Path) -> None:
    _setup(monkeypatch, tmp_path)
    profile = CandidateProfile(
        name="Test User",
        target_role="Backend",
        location="Remote",
        stacks=["Python"],
        links={},
        experiences=[],
        projects=[],
        education=[],
        preferences={},
    )

    first_job = JobPosting(
        external_id="https://www.linkedin.com/jobs/view/123",
        source="linkedin",
        url="https://www.linkedin.com/jobs/view/123",
        title="Backend Engineer",
        company="Acme",
        location="Remote",
        description="Short description",
        requirements=[],
    )
    improved_job = JobPosting(
        external_id="https://www.linkedin.com/jobs/view/123",
        source="linkedin",
        url="https://www.linkedin.com/jobs/view/123",
        title="Senior Backend Engineer",
        company="Acme Corp",
        location="Remote",
        description="Long enriched description with much better details about Python, APIs and cloud work.",
        requirements=[],
    )

    monkeypatch.setattr("src.domain.pipeline.collect_jobs", lambda *args, **kwargs: [first_job])
    run_pipeline(profile=profile, sources=["linkedin"], limit=1, rss_urls=[], manual_urls=[])

    monkeypatch.setattr("src.domain.pipeline.collect_jobs", lambda *args, **kwargs: [improved_job])
    run_pipeline(profile=profile, sources=["linkedin"], limit=1, rss_urls=[], manual_urls=[])

    with get_session() as session:
        repo = TrackerRepository(session)
        rows = [row for row in repo.list_jobs_all(min_score=0, user_id="default") if row.source == "linkedin"]

    assert len(rows) == 1
    assert rows[0].title == "Senior Backend Engineer"
    assert rows[0].company == "Acme Corp"
    assert "Long enriched description" in rows[0].description


def test_init_db_cleans_up_duplicate_linkedin_jobs(monkeypatch, tmp_path: Path) -> None:
    _setup(monkeypatch, tmp_path)

    with get_session() as session:
        repo = TrackerRepository(session)
        repo.upsert_job(
            id="job-old",
            user_id="default",
            run_id="run-old",
            external_id="https://www.linkedin.com/jobs/view/123",
            source="linkedin",
            url="https://www.linkedin.com/jobs/view/123",
            title="Backend EngineerBackend Engineer",
            company="AcmeAcme",
            location="remote",
            description="Short card description",
            score=55,
            score_reasons="",
            anchors_json="{}",
            score_breakdown_json="{}",
            recommendation="MAYBE",
            status="new",
        )
        repo.upsert_application(
            ApplicationRecord(id="app-job-old", job_id="job-old", status="prepared", recommendation="MAYBE"),
            link="https://www.linkedin.com/jobs/view/123",
            user_id="default",
            connector="linkedin",
        )
        repo.upsert_job(
            id="job-new",
            user_id="default",
            run_id="run-new",
            external_id="https://www.linkedin.com/jobs/view/123",
            source="linkedin",
            url="https://www.linkedin.com/jobs/view/123",
            title="Senior Backend Engineer",
            company="Acme Corp",
            location="remote",
            description="Long enriched description with Python, APIs and cloud work.",
            score=88,
            score_reasons="",
            anchors_json="{}",
            score_breakdown_json="{}",
            recommendation="APPLY",
            status="new",
        )

    init_db()

    with get_session() as session:
        repo = TrackerRepository(session)
        rows = [row for row in repo.list_jobs_all(min_score=0, user_id="default") if row.source == "linkedin"]
        application = repo.get_application("app-job-new", user_id="default")

    assert len(rows) == 1
    assert rows[0].id == "job-new"
    assert rows[0].title == "Senior Backend Engineer"
    assert application is not None
    assert application.job_id == "job-new"
