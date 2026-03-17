from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import httpx

from src.core.config import Settings
from src.domain.models import CandidateProfile, ConfidenceLevel, GeneratedAnswer, JobPosting


@dataclass(slots=True)
class ApplicationIntelligence:
    fit_summary: str
    answers: list[GeneratedAnswer]
    source: str


def generate_application_intelligence(settings: Settings, profile: CandidateProfile, job: JobPosting) -> ApplicationIntelligence:
    if not settings.llm_enabled or not settings.gemini_api_key:
        return _fallback_application_intelligence(job)
    try:
        return _generate_with_gemini(settings, profile, job)
    except Exception:
        return _fallback_application_intelligence(job)


def _generate_with_gemini(settings: Settings, profile: CandidateProfile, job: JobPosting) -> ApplicationIntelligence:
    prompt = _build_prompt(profile, job)
    response = httpx.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent",
        params={"key": settings.gemini_api_key},
        headers={"Content-Type": "application/json"},
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.3,
            },
        },
        timeout=45.0,
    )
    response.raise_for_status()
    payload = response.json()
    text = _extract_response_text(payload)
    parsed = json.loads(text)
    answers = [
        GeneratedAnswer(
            question=item["question"],
            answer=item["answer"],
            confidence=ConfidenceLevel(item.get("confidence", ConfidenceLevel.MEDIUM.value)),
            rationale=item.get("rationale", ""),
        )
        for item in parsed.get("answers", [])
    ]
    if not answers:
        raise ValueError("gemini returned no answers")
    return ApplicationIntelligence(
        fit_summary=parsed.get("fit_summary", f"Fit summary unavailable for {job.title} at {job.company}."),
        answers=answers,
        source="gemini",
    )


def _extract_response_text(payload: dict[str, Any]) -> str:
    candidates = payload.get("candidates", [])
    if not candidates:
        raise ValueError("gemini returned no candidates")
    parts = candidates[0].get("content", {}).get("parts", [])
    if not parts:
        raise ValueError("gemini returned no parts")
    text = parts[0].get("text", "")
    if not text:
        raise ValueError("gemini returned empty text")
    return text


def _build_prompt(profile: CandidateProfile, job: JobPosting) -> str:
    profile_blob = {
        "name": profile.name,
        "target_role": profile.target_role,
        "location": profile.location,
        "stacks": profile.stacks,
        "experiences": [item.model_dump() for item in profile.experiences],
        "projects": [item.model_dump() for item in profile.projects],
        "preferences": profile.preferences,
        "learning_plan": profile.learning_plan,
    }
    job_blob = {
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "description": job.description,
        "requirements": job.requirements,
        "source": job.source,
        "url": job.url,
    }
    return (
        "You are an application assistant. "
        "Return valid JSON only with keys fit_summary and answers. "
        "answers must be a list of 3 to 5 objects with question, answer, confidence, rationale. "
        "confidence must be one of high, medium, low. "
        "Do not invent facts beyond the supplied profile. "
        f"PROFILE={json.dumps(profile_blob, ensure_ascii=False)} "
        f"JOB={json.dumps(job_blob, ensure_ascii=False)}"
    )


def _fallback_application_intelligence(job: JobPosting) -> ApplicationIntelligence:
    return ApplicationIntelligence(
        fit_summary=f"My profile is strongest in hands-on delivery, product mindset and practical execution for roles like {job.title} at {job.company}.",
        answers=[
            GeneratedAnswer(
                question="Why are you interested in this role?",
                answer=f"I am targeting roles like {job.title} and see a strong fit between my background and {job.company}.",
                confidence=ConfidenceLevel.HIGH,
                rationale="Uses target role and company context from the saved profile.",
            ),
            GeneratedAnswer(
                question="What is your notice period?",
                answer="I can discuss start date quickly and align to the company's hiring timeline.",
                confidence=ConfidenceLevel.MEDIUM,
                rationale="Safe default without inventing legal or contractual details.",
            ),
            GeneratedAnswer(
                question="Can you share a short fit summary?",
                answer=f"My profile is strongest in hands-on delivery, product mindset and practical execution for teams like {job.company}.",
                confidence=ConfidenceLevel.MEDIUM,
                rationale="Summarizes fit in a reusable application-safe way.",
            ),
        ],
        source="fallback",
    )
