from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import httpx

from src.core.config import Settings
from src.domain.models import CandidateProfile, JobPosting, ScoringResult
from src.domain.scoring import recommendation_from_score


@dataclass(slots=True)
class JobFitIntelligence:
    fit_summary: str
    recommendation: str
    reasons: list[str]
    gaps: list[str]
    top_matched_terms: list[str]
    llm_adjustment: int
    source: str


def augment_job_fit_with_llm(
    settings: Settings,
    profile: CandidateProfile,
    job: JobPosting,
    baseline: ScoringResult,
) -> JobFitIntelligence:
    if not settings.llm_enabled or not settings.gemini_api_key:
        return _fallback_fit(job, baseline)
    try:
        return _generate_job_fit_with_gemini(settings, profile, job, baseline)
    except Exception:
        return _fallback_fit(job, baseline)


def _generate_job_fit_with_gemini(
    settings: Settings,
    profile: CandidateProfile,
    job: JobPosting,
    baseline: ScoringResult,
) -> JobFitIntelligence:
    prompt = _build_fit_prompt(profile, job, baseline)
    response = httpx.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent",
        params={"key": settings.gemini_api_key},
        headers={"Content-Type": "application/json"},
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.2,
            },
        },
        timeout=45.0,
    )
    response.raise_for_status()
    payload = response.json()
    text = payload["candidates"][0]["content"]["parts"][0]["text"]
    parsed = json.loads(text)

    recommendation = parsed.get("recommendation", recommendation_from_score(baseline.score))
    if recommendation not in {"APPLY", "MAYBE", "SKIP"}:
        recommendation = recommendation_from_score(baseline.score)

    llm_adjustment = int(parsed.get("llm_adjustment", 0))
    llm_adjustment = max(-15, min(15, llm_adjustment))

    return JobFitIntelligence(
        fit_summary=parsed.get("fit_summary", ""),
        recommendation=recommendation,
        reasons=[str(item) for item in parsed.get("reasons", [])][:6] or baseline.reasons,
        gaps=[str(item) for item in parsed.get("gaps", [])][:6] or baseline.gaps,
        top_matched_terms=[str(item) for item in parsed.get("top_matched_terms", [])][:8] or baseline.top_matched_terms,
        llm_adjustment=llm_adjustment,
        source="gemini",
    )


def _build_fit_prompt(profile: CandidateProfile, job: JobPosting, baseline: ScoringResult) -> str:
    return (
        "You are a hiring fit evaluator. "
        "Return JSON only with keys fit_summary, recommendation, reasons, gaps, top_matched_terms, llm_adjustment. "
        "recommendation must be APPLY, MAYBE, or SKIP. "
        "llm_adjustment must be an integer between -15 and 15. "
        "Do not invent profile experience beyond the supplied data. "
        f"PROFILE={json.dumps(profile.model_dump(), ensure_ascii=False)} "
        f"JOB={json.dumps(job.model_dump(), ensure_ascii=False)} "
        f"BASELINE={json.dumps(baseline.model_dump(), ensure_ascii=False)}"
    )


def _fallback_fit(job: JobPosting, baseline: ScoringResult) -> JobFitIntelligence:
    return JobFitIntelligence(
        fit_summary=f"Baseline fit for {job.title} at {job.company} based on stack, seniority, location and keyword overlap.",
        recommendation=recommendation_from_score(baseline.score),
        reasons=baseline.reasons,
        gaps=baseline.gaps,
        top_matched_terms=baseline.top_matched_terms,
        llm_adjustment=0,
        source="fallback",
    )
