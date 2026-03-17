import json

from src.core.config import get_settings
from src.domain.models import CandidateProfile, ExperienceItem, JobPosting, ProjectItem
from src.services.llm_service import generate_application_intelligence


def _profile() -> CandidateProfile:
    return CandidateProfile(
        name="Ana",
        target_role="Backend Engineer",
        location="Remote",
        stacks=["Python", "FastAPI", "SQL"],
        links={"github": "https://github.com/ana"},
        experiences=[ExperienceItem(company="Acme", period="2024", bullets=["Built APIs with FastAPI"])],
        projects=[ProjectItem(name="TaskFlow", description="Automation app", stack=["Python"], links=[])],
        education=["ADS"],
        preferences={"company_type": "produto"},
        bullet_bank={},
        learning_plan=[],
    )


def _job() -> JobPosting:
    return JobPosting(
        external_id="1",
        source="manual",
        url="https://example.com/job",
        title="Backend Engineer",
        company="Beta",
        location="Remote",
        description="Need Python and FastAPI",
        requirements=["Python", "FastAPI"],
    )


def test_generate_application_intelligence_uses_gemini_when_enabled(monkeypatch) -> None:
    monkeypatch.setenv("LLM_ENABLED", "true")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    get_settings.cache_clear()

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": json.dumps(
                                        {
                                            "fit_summary": "Strong API fit.",
                                            "answers": [
                                                {
                                                    "question": "Why are you interested in this role?",
                                                    "answer": "I have strong backend experience.",
                                                    "confidence": "high",
                                                    "rationale": "Matches stack.",
                                                }
                                            ],
                                        }
                                    )
                                }
                            ]
                        }
                    }
                ]
            }

    monkeypatch.setattr("src.services.llm_service.httpx.post", lambda *args, **kwargs: FakeResponse())
    result = generate_application_intelligence(get_settings(), _profile(), _job())

    assert result.source == "gemini"
    assert result.fit_summary == "Strong API fit."
    assert result.answers[0].confidence.value == "high"


def test_generate_application_intelligence_falls_back_on_failure(monkeypatch) -> None:
    monkeypatch.setenv("LLM_ENABLED", "true")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    get_settings.cache_clear()

    def fail(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("src.services.llm_service.httpx.post", fail)
    result = generate_application_intelligence(get_settings(), _profile(), _job())

    assert result.source == "fallback"
    assert result.fit_summary
    assert len(result.answers) >= 1
