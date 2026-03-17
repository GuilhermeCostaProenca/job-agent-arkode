from src.domain.models import CandidateProfile
from src.ingest.sources.linkedin import _matches_profile_focus


def _profile() -> CandidateProfile:
    return CandidateProfile(
        name="Test User",
        target_role="Estágio/Júnior em Desenvolvimento",
        location="SP/remoto",
        stacks=["Flutter", "Kotlin", "Java", "SQL", "Power BI"],
        links={},
        experiences=[],
        projects=[],
        education=[],
        preferences={},
    )


def test_matches_profile_focus_accepts_technical_role() -> None:
    item = {
        "title": "Junior Java Developer",
        "description": "Build backend APIs with Java, SQL and cloud integrations.",
        "location": "Brasil (Remoto)",
    }

    assert _matches_profile_focus(_profile(), item) is True


def test_matches_profile_focus_rejects_irrelevant_kya_like_role() -> None:
    item = {
        "title": "Senior KYC Analist",
        "description": "Compliance, AML, risk analysis and stakeholder management in banking.",
        "location": "Países Baixos (Remoto)",
    }

    assert _matches_profile_focus(_profile(), item) is False


def test_matches_profile_focus_rejects_content_review_noise() -> None:
    item = {
        "title": "Content Reviewer",
        "description": "Review online content, taxonomy and moderation guidelines for AI responses.",
        "location": "Países Baixos (Remoto)",
    }

    assert _matches_profile_focus(_profile(), item) is False
