from pathlib import Path

from fastapi.testclient import TestClient

from src.api.main import app
from src.core.config import get_settings
from src.tracker.db import get_session, init_db
from src.tracker.repo import TrackerRepository


def _setup_db(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "api_reliability.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("USER_ID", "default")
    get_settings.cache_clear()
    init_db()


def test_generate_drafts_returns_text_content(monkeypatch, tmp_path: Path) -> None:
    _setup_db(monkeypatch, tmp_path)

    with get_session() as session:
        repo = TrackerRepository(session)
        repo.create_feed_item(
            feed_id="feed-1",
            source="manual",
            url="https://example.com/post",
            text="we're hiring flutter engineers",
            is_hiring=True,
            confidence=0.95,
            user_id="default",
        )

    client = TestClient(app)
    response = client.post("/feed/feed-1/generate-drafts")

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"comment", "dm", "email"}
    assert isinstance(body["comment"], str)
    assert "Comentario sugerido" in body["comment"]
    assert "/artifacts/" not in body["comment"]


def test_generate_drafts_returns_404_for_missing_feed_item(monkeypatch, tmp_path: Path) -> None:
    _setup_db(monkeypatch, tmp_path)

    client = TestClient(app)
    response = client.post("/feed/missing-feed/generate-drafts")

    assert response.status_code == 404
    assert response.json()["detail"] == "feed item not found"
