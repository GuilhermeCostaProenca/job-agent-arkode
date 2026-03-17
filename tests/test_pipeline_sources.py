from src.domain.models import CandidateProfile, ExperienceItem, JobPosting, ProjectItem
from src.domain.pipeline import collect_jobs


def _profile() -> CandidateProfile:
    return CandidateProfile(
        name="Ana",
        target_role="Junior Backend Engineer",
        location="remoto",
        stacks=["Python", "FastAPI", "SQL"],
        links={"linkedin": "https://www.linkedin.com/in/ana"},
        experiences=[ExperienceItem(company="Acme", period="2025", bullets=["Built APIs"])],
        projects=[ProjectItem(name="TaskFlow", description="Automation", stack=["Python"], links=[])],
        education=["ADS"],
        preferences={},
        bullet_bank={},
        learning_plan=[],
    )


def test_collect_jobs_includes_linkedin_source(monkeypatch) -> None:
    monkeypatch.setattr("src.domain.pipeline.fetch_rss_jobs", lambda rss_urls, limit: [])
    monkeypatch.setattr("src.domain.pipeline.fetch_manual_url", lambda url: JobPosting(
        external_id=url,
        source="manual",
        url=url,
        title="Manual Job",
        company="Manual Co",
        location="Remote",
        description="Manual description",
        requirements=[],
    ))
    monkeypatch.setattr(
        "src.domain.pipeline.fetch_linkedin_jobs",
        lambda settings, profile, limit: [
            JobPosting(
                external_id="https://www.linkedin.com/jobs/view/123",
                source="linkedin",
                url="https://www.linkedin.com/jobs/view/123",
                title="LinkedIn Backend Engineer",
                company="LinkedIn Co",
                location="Remote",
                description="Need Python and FastAPI",
                requirements=[],
            )
        ],
    )

    jobs = collect_jobs(["linkedin", "manual"], limit=5, rss_urls=[], manual_urls=["https://example.com/job"], profile=_profile())

    assert any(job.source == "linkedin" for job in jobs)
    assert any(job.source == "manual" for job in jobs)
