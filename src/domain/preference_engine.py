from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.domain.models import JobAnchors

DEFAULT_WEIGHTS: dict[str, Any] = {
    "skills": {},
    "locations": {"remote": 1.0, "hybrid_sp": 0.5, "onsite_far": -1.0},
    "seniority": {"intern": 1.0, "junior": 1.0, "mid": -0.5, "senior": -1.0},
    "company_type": {"product": 1.0, "consulting": 0.2, "bodyshop": -0.8},
    "red_flags": {"unpaid": -2.0, "pj_abusive": -1.5, "support_disguised": -1.0},
    "writing_style": {"directness": 0.0, "formality": 0.0, "confidence": 0.0},
    "last_processed_signal_id": "",
}


@dataclass
class PreferenceModel:
    weights: dict[str, Any]


def _clamp(value: float, lower: float = -3.0, upper: float = 3.0) -> float:
    return max(lower, min(upper, value))


def load_preference_model(repo: Any, user_id: str = "default") -> PreferenceModel:
    row = repo.get_preference_model(user_id=user_id)
    if row is None:
        repo.upsert_preference_model("default", DEFAULT_WEIGHTS, user_id=user_id)
        return PreferenceModel(weights={**DEFAULT_WEIGHTS})
    merged = {**DEFAULT_WEIGHTS, **row}
    return PreferenceModel(weights=merged)


def update_preferences_from_signal(
    signal: Any,
    job: Any,
    anchors: JobAnchors,
    weights: dict[str, Any],
) -> dict[str, Any]:
    skills = weights.setdefault("skills", {})
    delta = 0.05
    if signal.signal_type in {"applied", "interview", "offer"}:
        delta = 0.12
    elif signal.signal_type in {"approval", "artifact_edit"}:
        delta = 0.07
    elif signal.signal_type in {"rejection"}:
        delta = -0.1

    for skill in anchors.top_skills[:8]:
        current = float(skills.get(skill, 0.0))
        skills[skill] = _clamp(current + delta)

    reason = (
        str(signal.payload_json.get("reason", "")).lower()
        if isinstance(signal.payload_json, dict)
        else ""
    )
    locations = weights.setdefault("locations", {})
    if "local" in reason or "presencial" in reason:
        locations["onsite_far"] = _clamp(float(locations.get("onsite_far", -1.0)) - 0.2)

    weights["last_processed_signal_id"] = signal.id
    return weights


def apply_preferences_to_score(
    job: Any,
    anchors: JobAnchors,
    base_score_breakdown: dict[str, int],
    weights: dict[str, Any],
) -> tuple[int, dict[str, float]]:
    adjustments: dict[str, float] = {
        "skills_pref": 0.0,
        "location_pref": 0.0,
        "seniority_pref": 0.0,
    }
    skill_weights = weights.get("skills", {})
    for skill in anchors.top_skills[:6]:
        adjustments["skills_pref"] += float(skill_weights.get(skill, 0.0))

    location = str(getattr(job, "location", "")).lower()
    loc_weights = weights.get("locations", {})
    if "remoto" in location or "remote" in location:
        adjustments["location_pref"] += float(loc_weights.get("remote", 0.0))
    elif "híbrido" in location or "hybrid" in location:
        adjustments["location_pref"] += float(loc_weights.get("hybrid_sp", 0.0))
    else:
        adjustments["location_pref"] += float(loc_weights.get("onsite_far", -0.5))

    title = str(getattr(job, "title", "")).lower()
    seniority = weights.get("seniority", {})
    if "est" in title or "intern" in title:
        adjustments["seniority_pref"] += float(seniority.get("intern", 0.0))
    elif "jun" in title:
        adjustments["seniority_pref"] += float(seniority.get("junior", 0.0))
    elif "senior" in title:
        adjustments["seniority_pref"] += float(seniority.get("senior", 0.0))
    else:
        adjustments["seniority_pref"] += float(seniority.get("mid", 0.0))

    base_score = (
        int(base_score_breakdown.get("skill_match_score", 0))
        + int(base_score_breakdown.get("seniority_score", 0))
        + int(base_score_breakdown.get("location_score", 0))
        + int(base_score_breakdown.get("keyword_density_score", 0))
        - int(base_score_breakdown.get("red_flag_penalty", 0))
    )
    adjusted_score = max(0, min(100, int(round(base_score + sum(adjustments.values())))))
    return adjusted_score, adjustments
