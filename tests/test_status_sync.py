from src.core.config import get_settings
from src.domain.models import ApplicationRecord
from src.tracker.db import get_session, init_db
from src.tracker.repo import TrackerRepository


def _seed_job(repo: TrackerRepository) -> None:
    repo.upsert_job(
        id="job-1",
        user_id="default",
        run_id="run-1",
        external_id="ext-1",
        source="manual",
        url="https://example.com/job-1",
        title="Dev Junior",
        company="Acme",
        location="remote",
        description="desc",
        score=80,
        score_reasons="",
        anchors_json="{}",
        score_breakdown_json="{}",
        recommendation="APPLY",
        status="new",
    )


def test_application_status_syncs_job_status(monkeypatch, tmp_path) -> None:
    db_path = tmp_path / "status.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("USER_ID", "default")
    get_settings.cache_clear()
    init_db()

    with get_session() as session:
        repo = TrackerRepository(session)
        _seed_job(repo)
        repo.upsert_application(ApplicationRecord(id="app-1", job_id="job-1", status="prepared"), link="https://example.com/job-1", user_id="default")
        job = repo.get_job("job-1")
        assert job is not None
        assert job.status == "new"

        repo.update_application_status("job-1", "reviewed", user_id="default")
        assert repo.get_job("job-1").status == "reviewed"  # type: ignore[union-attr]

        repo.update_application_status("job-1", "applied", user_id="default")
        assert repo.get_job("job-1").status == "applied"  # type: ignore[union-attr]

        repo.update_application_status("job-1", "rejected", user_id="default")
        assert repo.get_job("job-1").status == "rejected"  # type: ignore[union-attr]


def test_approved_application_maps_to_reviewed_job(monkeypatch, tmp_path) -> None:
    db_path = tmp_path / "approved.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("USER_ID", "default")
    get_settings.cache_clear()
    init_db()

    with get_session() as session:
        repo = TrackerRepository(session)
        _seed_job(repo)
        repo.upsert_application(ApplicationRecord(id="app-1", job_id="job-1", status="prepared"), link="https://example.com/job-1", user_id="default")
        repo.update_application_status("job-1", "approved", user_id="default")
        job = repo.get_job("job-1")
        assert job is not None
        assert job.status == "reviewed"
