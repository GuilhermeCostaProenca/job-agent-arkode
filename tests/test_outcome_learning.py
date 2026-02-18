from src.domain.anchors import extract_job_anchors
from src.domain.models import JobPosting
from src.domain.preference_engine import DEFAULT_WEIGHTS, update_preferences_from_signal


class DummySignal:
    def __init__(self, signal_type: str):
        self.signal_type = signal_type
        self.payload_json = {}
        self.id = signal_type


def test_outcome_weighted_learning_stronger_than_approval() -> None:
    job = JobPosting(
        external_id="1",
        source="rss",
        url="u",
        title="Flutter Dev",
        company="Acme",
        location="remote",
        description="flutter",
    )
    anchors = extract_job_anchors(job)

    w1 = {**DEFAULT_WEIGHTS, "skills": {}}
    w1 = update_preferences_from_signal(DummySignal("approval"), job, anchors, w1)
    approval_flutter = float(w1["skills"].get("flutter", 0.0))

    w2 = {**DEFAULT_WEIGHTS, "skills": {}}
    for typ in ["approval", "applied", "replied", "interview"]:
        w2 = update_preferences_from_signal(DummySignal(typ), job, anchors, w2)
    chain_flutter = float(w2["skills"].get("flutter", 0.0))

    assert chain_flutter > approval_flutter
