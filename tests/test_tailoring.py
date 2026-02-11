from pathlib import Path

from src.domain.models import CandidateProfile, ExperienceItem, JobPosting, ProjectItem
from src.domain.tailoring import build_artifacts


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


def test_tailoring_generates_artifacts(tmp_path: Path) -> None:
    profile = build_profile()
    job = JobPosting(
        external_id="job-1",
        source="manual",
        url="https://example.com/job",
        title="Dev Mobile",
        company="Acme",
        location="remoto",
        description="Flutter e SQL",
        requirements=["Flutter", "SQL", "Power BI"],
    )

    bundle = build_artifacts(job, profile, tmp_path)
    assert Path(bundle.resume_path).exists()
    assert len(bundle.cover_paths) == 3
    assert Path(bundle.checklist_path).exists()
