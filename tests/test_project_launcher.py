from src.domain.anchors import extract_job_anchors
from src.domain.models import CandidateProfile, ExperienceItem, JobPosting, ProjectItem
from src.domain.project_launcher import generate_project_prompt


def test_project_prompt_generation_contains_structure() -> None:
    job = JobPosting(
        external_id="j1",
        source="rss",
        url="https://example.com/job",
        title="Data Intern",
        company="Acme",
        location="Remoto",
        description="Requisitos: SQL, dashboard, Power BI",
    )
    profile = CandidateProfile(
        name="Ana",
        target_role="Estágio",
        location="SP/remoto",
        stacks=["SQL", "Power BI", "Python"],
        links={"github": "x"},
        experiences=[ExperienceItem(company="A", period="2024", bullets=["b"])],
        projects=[ProjectItem(name="P", description="d", stack=["SQL"], links=[])],
        education=["ADS"],
        preferences={"company_type": "produto"},
    )
    anchors = extract_job_anchors(job)
    prompt = generate_project_prompt(job, anchors, profile)
    assert "User stories" in prompt
    assert "Estrutura de pastas" in prompt
