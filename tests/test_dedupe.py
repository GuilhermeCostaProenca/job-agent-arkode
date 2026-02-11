from src.domain.models import JobPosting
from src.ingest.dedupe import dedupe_jobs


def test_dedupe_jobs_removes_duplicates() -> None:
    base = JobPosting(
        external_id="x",
        source="rss",
        url="https://example.com/1",
        title="Engenheiro de Software",
        company="Acme",
        location="SP",
        description="vaga python",
    )
    dup = base.model_copy(deep=True)
    dup.external_id = "y"
    jobs = dedupe_jobs([base, dup])
    assert len(jobs) == 1
