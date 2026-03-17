import json

from src.core.config import get_settings
from src.domain.models import CandidateProfile, ExperienceItem, JobPosting, ProjectItem
from src.domain.scoring import score_job
from src.services.job_fit_service import augment_job_fit_with_llm


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


def test_augment_job_fit_with_llm_uses_gemini(monkeypatch) -> None:
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
                                            "fit_summary": "Very strong backend fit.",
                                            "recommendation": "APPLY",
                                            "reasons": ["Strong overlap in backend stack"],
                                            "gaps": ["No major gaps"],
                                            "top_matched_terms": ["python", "fastapi"],
                                            "llm_adjustment": 8,
                                        }
                                    )
                                }
                            ]
                        }
                    }
                ]
            }

    monkeypatch.setattr("src.services.job_fit_service.httpx.post", lambda *args, **kwargs: FakeResponse())
    baseline = score_job(_job(), _profile())
    result = augment_job_fit_with_llm(get_settings(), _profile(), _job(), baseline)

    assert result.source == "gemini"
    assert result.recommendation == "APPLY"
    assert result.llm_adjustment == 8
    assert result.fit_summary == "Very strong backend fit."


def test_augment_job_fit_with_llm_falls_back(monkeypatch) -> None:
    monkeypatch.setenv("LLM_ENABLED", "true")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    get_settings.cache_clear()
    monkeypatch.setattr("src.services.job_fit_service.httpx.post", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")))

    baseline = score_job(_job(), _profile())
    result = augment_job_fit_with_llm(get_settings(), _profile(), _job(), baseline)

    assert result.source == "fallback"
    assert result.recommendation in {"APPLY", "MAYBE", "SKIP"}
