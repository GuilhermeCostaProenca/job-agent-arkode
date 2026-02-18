from src.domain.models import CandidateProfile, ExperienceItem, JobPosting, ProjectItem
from src.domain.scoring import recommendation_from_score, score_job


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
        bullet_bank={"mobile": ["Entreguei feature Flutter com impacto em retenção."]},
        learning_plan=["Power BI"],
    )


def test_scoring_returns_breakdown_and_explanations() -> None:
    profile = build_profile()
    job = JobPosting(
        external_id="1",
        source="rss",
        url="https://example.com/job",
        title="Desenvolvedor Mobile Júnior",
        company="Acme",
        location="Remoto",
        description="Precisamos de Kotlin e SQL para app mobile",
        requirements=["Kotlin", "SQL"],
    )

    result = score_job(job, profile)
    assert 0 <= result.score <= 100
    assert result.breakdown.skill_match_score >= 0
    assert recommendation_from_score(result.score) in {"APPLY", "MAYBE", "SKIP"}
