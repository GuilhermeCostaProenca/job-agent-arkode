from __future__ import annotations

from src.core.utils import normalize_text
from src.domain.models import CandidateProfile, JobPosting, ScoreBreakdown, ScoringResult


def recommendation_from_score(score: int) -> str:
    if score >= 80:
        return "APPLY"
    if score >= 60:
        return "MAYBE"
    return "SKIP"


def score_job(job: JobPosting, profile: CandidateProfile) -> ScoringResult:
    reasons: list[str] = []
    desc = normalize_text(job.description)
    req_text = normalize_text(" ".join(job.requirements))

    profile_skills = {skill.lower() for skill in profile.stacks}
    hits = sorted(skill for skill in profile_skills if skill in desc or skill in req_text)
    gaps = sorted(skill for skill in profile_skills if skill not in hits)

    skill_match_score = min(35, int((len(hits) / max(len(profile_skills), 1)) * 35))

    target_role = profile.target_role.lower()
    title_lower = job.title.lower()
    if any(word in title_lower for word in ["estágio", "junior", "júnior", "trainee"]) and (
        "jun" in target_role or "est" in target_role
    ):
        seniority_score = 20
    else:
        seniority_score = 10

    preferred_location = profile.location.lower()
    location_lower = job.location.lower()
    if "remoto" in location_lower or preferred_location in location_lower:
        location_score = 15
    else:
        location_score = 6

    keyword_density_score = min(30, int(((len(hits) * 2) + len(job.requirements)) / 2))

    red_flag_penalty = 0
    if "senior" in desc and ("jun" in target_role or "est" in target_role):
        red_flag_penalty += 15
    if "10+" in desc or "10 anos" in desc:
        red_flag_penalty += 10

    breakdown = ScoreBreakdown(
        skill_match_score=skill_match_score,
        seniority_score=seniority_score,
        location_score=location_score,
        keyword_density_score=keyword_density_score,
        red_flag_penalty=red_flag_penalty,
    )
    score = max(
        0,
        min(
            100,
            breakdown.skill_match_score
            + breakdown.seniority_score
            + breakdown.location_score
            + breakdown.keyword_density_score
            - breakdown.red_flag_penalty,
        ),
    )

    reasons.append(f"skills +{breakdown.skill_match_score}")
    reasons.append(f"seniority +{breakdown.seniority_score}")
    reasons.append(f"location +{breakdown.location_score}")
    reasons.append(f"keywords +{breakdown.keyword_density_score}")
    reasons.append(f"red_flags -{breakdown.red_flag_penalty}")
    reasons.append(f"recommendation {recommendation_from_score(score)}")
    reasons.append(f"score final {score}")

    return ScoringResult(
        score=score,
        reasons=reasons,
        breakdown=breakdown,
        top_matched_terms=hits,
        gaps=gaps,
    )
