from pathlib import Path

from src.core.config import get_settings
from src.tracker.db import get_session, init_db
from src.tracker.repo import TrackerRepository


def test_recommendations_include_exploration(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "explore.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("USER_ID", "default")
    get_settings.cache_clear()
    init_db()

    with get_session() as session:
        repo = TrackerRepository(session)
        for i in range(10):
            repo.upsert_job(
                id=f"job-{i}",
                user_id="default",
                run_id="run-1",
                external_id=f"e-{i}",
                source="rss",
                url=f"https://example.com/{i}",
                title="Dev Flutter" if i < 8 else "Dev Rust",
                company=f"Acme{i}",
                location="remote" if i < 8 else "porto alegre",
                description="d",
                score=90 - i,
                score_reasons="",
                anchors_json='{"top_skills":["flutter"]}' if i < 8 else '{"top_skills":["rust"]}',
                score_breakdown_json="{}",
                recommendation="MAYBE",
                status="new",
            )
        rows = repo.list_recommendations(min_score=60, limit=10, explore=True)

    assert len(rows) == 10
    assert any(item["is_exploration"] for item in rows)
