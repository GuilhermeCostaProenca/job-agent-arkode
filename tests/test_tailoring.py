from pathlib import Path

from src.domain.anchors import extract_job_anchors
from src.domain.models import CandidateProfile, ExperienceItem, JobPosting, ProjectItem
from src.domain.scoring import score_job
from src.domain.tailoring import build_artifacts, select_relevant_bullets


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
        bullet_bank={
            "mobile": ["Implementei fluxo Flutter com melhoria de performance perceptível."],
            "data": ["Criei dashboard SQL/BI para acompanhamento semanal."],
        },
        learning_plan=["Aprofundar backend"],
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
        description="Requisitos: Flutter e SQL",
        requirements=["Flutter", "SQL", "Power BI"],
    )
    anchors = extract_job_anchors(job)
    scoring = score_job(job, profile)

    bundle = build_artifacts(job, profile, tmp_path, anchors, scoring)
    assert Path(bundle.resume_path).exists()
    assert len(bundle.cover_paths) == 3
    assert Path(bundle.checklist_path).exists()
    assert Path(bundle.match_analysis_path).exists()
    assert Path(bundle.project_prompt_path).exists()


def test_select_relevant_bullets_prefers_matching_bank() -> None:
    profile = build_profile()
    job = JobPosting(
        external_id="2",
        source="rss",
        url="https://example.com/2",
        title="Mobile",
        company="x",
        location="remoto",
        description="flutter sql",
    )
    anchors = extract_job_anchors(job)
    bullets = select_relevant_bullets(profile, anchors)
    assert any("Flutter" in bullet or "flutter" in bullet for bullet in bullets)
