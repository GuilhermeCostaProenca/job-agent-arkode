from __future__ import annotations

from src.core.utils import normalize_text
from src.domain.models import CandidateProfile, JobPosting, ScoringResult


def score_job(job: JobPosting, profile: CandidateProfile) -> ScoringResult:
    reasons: list[str] = []
    score = 0
    desc = normalize_text(job.description)
    req_text = normalize_text(" ".join(job.requirements))

    profile_skills = {skill.lower() for skill in profile.stacks}
    hits = [skill for skill in profile_skills if skill in desc or skill in req_text]
    overlap_ratio = len(hits) / max(len(profile_skills), 1)
    skills_score = min(45, int(overlap_ratio * 55))
    score += skills_score
    reasons.append(f"Skills compatíveis: {len(hits)}/{len(profile_skills)} (+{skills_score})")

    target_role = profile.target_role.lower()
    title_lower = job.title.lower()
    if any(word in title_lower for word in ["estágio", "junior", "júnior", "trainee"]) and (
        "jun" in target_role or "est" in target_role
    ):
        score += 20
        reasons.append("Senioridade alinhada (+20)")
    else:
        score += 8
        reasons.append("Senioridade parcialmente alinhada (+8)")

    preferred_location = profile.location.lower()
    location_lower = job.location.lower()
    if "remoto" in location_lower or preferred_location in location_lower:
        score += 20
        reasons.append("Localização compatível (+20)")
    else:
        score += 5
        reasons.append("Localização não ideal (+5)")

    red_flag_penalty = 0
    if "senior" in desc and ("jun" in target_role or "est" in target_role):
        red_flag_penalty += 15
        reasons.append("Red flag: vaga senior para perfil júnior (-15)")
    if "10+" in desc or "10 anos" in desc:
        red_flag_penalty += 10
        reasons.append("Red flag: exigência de muitos anos de experiência (-10)")

    score = max(0, min(100, score - red_flag_penalty))
    reasons.append(f"Score final: {score}")
    return ScoringResult(score=score, reasons=reasons)
