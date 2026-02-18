from pathlib import Path

from src.core.config import get_settings
from src.domain.anchors import extract_job_anchors
from src.domain.models import JobPosting
from src.domain.preference_engine import (
    apply_preferences_to_score,
    load_preference_model,
    update_preferences_from_signal,
)
from src.domain.signals import Signal, record_signal
from src.tracker.db import get_session, init_db
from src.tracker.repo import TrackerRepository


def test_signal_tables_creation_and_insert(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "signals.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("USER_ID", "default")
    get_settings.cache_clear()
    init_db()

    with get_session() as session:
        repo = TrackerRepository(session)
        record_signal(repo, Signal(signal_type="approval", job_id="job-1", payload={"ok": True}))
        rows = repo.list_signals(limit=10)
    assert len(rows) == 1


def test_preference_learning_increases_flutter_weight(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "pref.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    get_settings.cache_clear()
    init_db()

    job = JobPosting(
        external_id="1",
        source="rss",
        url="u",
        title="Flutter Dev",
        company="Acme",
        location="Remoto",
        description="flutter sql",
    )
    anchors = extract_job_anchors(job)

    with get_session() as session:
        repo = TrackerRepository(session)
        repo.upsert_preference_model("default", {"skills": {}, "last_processed_signal_id": ""})
        weights = load_preference_model(repo).weights
        for i in range(3):
            signal = Signal(signal_type="approval", job_id="j", payload={}, run_id=str(i))

            class X:  # lightweight wrapper
                signal_type = signal.signal_type
                payload_json = signal.payload
                id = signal.id

            weights = update_preferences_from_signal(X(), job, anchors, weights)
        repo.upsert_preference_model("default", weights)

    flutter = float(weights.get("skills", {}).get("flutter", 0.0))
    adjusted, _ = apply_preferences_to_score(
        job,
        anchors,
        {
            "skill_match_score": 20,
            "seniority_score": 10,
            "location_score": 10,
            "keyword_density_score": 10,
            "red_flag_penalty": 0,
        },
        weights,
    )
    assert flutter > 0
    assert adjusted >= 50
