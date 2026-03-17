from __future__ import annotations

import re
from typing import Any

from src.autopilot.linkedin_easy_apply import LinkedInPlaywrightRuntime
from src.core.config import Settings
from src.tracker.repo import JobTable, TrackerRepository


def repair_linkedin_jobs(repo: TrackerRepository, settings: Settings, limit: int = 10) -> dict[str, Any]:
    candidates = [_serialize_job(row) for row in repo.list_jobs_all(min_score=0, user_id=settings.user_id) if row.source == "linkedin" and _needs_repair(row)]
    candidates = candidates[:limit]
    runtime = LinkedInPlaywrightRuntime(
        profile_dir=settings.browser_storage_dir / "linkedin",
        artifacts_dir=settings.artifacts_dir,
        headless=settings.playwright_headless,
    )
    repaired: list[dict[str, str]] = []
    try:
        for candidate in candidates:
            enriched = runtime.scrape_job_details(candidate)
            cleaned = _clean_repaired_job(candidate, enriched)
            repo.upsert_job(
                id=candidate["id"],
                user_id=settings.user_id,
                run_id=candidate["run_id"],
                external_id=candidate["external_id"],
                source="linkedin",
                url=cleaned["url"],
                title=cleaned["title"],
                company=cleaned["company"],
                location=cleaned["location"],
                description=cleaned["description"],
                score=candidate["score"],
                score_reasons=candidate["score_reasons"],
                anchors_json=candidate["anchors_json"],
                score_breakdown_json=candidate["score_breakdown_json"],
                recommendation=candidate["recommendation"],
                status=candidate["status"],
            )
            repaired.append(
                {
                    "id": candidate["id"],
                    "url": cleaned["url"],
                    "title": cleaned["title"],
                    "company": cleaned["company"],
                }
            )
    finally:
        runtime.close()

    return {
        "status": "completed",
        "message": f"Foram reparadas {len(repaired)} vagas antigas do LinkedIn.",
        "repaired_jobs": repaired,
    }


def _needs_repair(row: JobTable) -> bool:
    title = row.title.strip()
    description = row.description.strip()
    return (
        _looks_duplicated(title)
        or len(description) < 300
        or "candidatura simplificada" in description.lower()
        or "avaliando candidaturas" in description.lower()
    )


def _looks_duplicated(value: str) -> bool:
    normalized = " ".join(value.lower().split())
    if not normalized:
        return False
    midpoint = len(normalized) // 2
    if len(normalized) % 2 == 0 and normalized[:midpoint] == normalized[midpoint:]:
        return True
    words = normalized.split(" ")
    if len(words) % 2 == 0:
        half = len(words) // 2
        return words[:half] == words[half:]
    return False


def _serialize_job(row: JobTable) -> dict[str, str | int]:
    return {
        "id": row.id,
        "run_id": row.run_id,
        "external_id": row.external_id,
        "url": row.url,
        "title": row.title,
        "company": row.company,
        "location": row.location,
        "description": row.description,
        "score": row.score,
        "score_reasons": row.score_reasons,
        "anchors_json": row.anchors_json,
        "score_breakdown_json": row.score_breakdown_json,
        "recommendation": row.recommendation,
        "status": row.status,
    }


def _clean_repaired_job(candidate: dict[str, str | int], enriched: dict[str, str]) -> dict[str, str]:
    title = _collapse_repeated(enriched.get("title") or str(candidate["title"]))
    company = _collapse_repeated(enriched.get("company") or str(candidate["company"]))
    location = _collapse_repeated(enriched.get("location") or str(candidate["location"]))
    description = _normalize_whitespace(enriched.get("description") or str(candidate["description"]))

    if description:
        description = _strip_card_prefix(description, title, company, location)
    if _looks_like_card_description(description):
        description = _normalize_whitespace(str(candidate["description"]))
        description = _strip_card_prefix(description, title, company, location)

    if _looks_duplicated(title) and description:
        inferred_title = _infer_title_from_description(description)
        if inferred_title:
            title = inferred_title

    return {
        "url": str(enriched.get("url") or candidate["url"]),
        "title": title,
        "company": company,
        "location": location,
        "description": description or str(candidate["description"]),
    }


def _collapse_repeated(value: str) -> str:
    normalized = _normalize_whitespace(value)
    if not normalized:
        return ""
    midpoint = len(normalized) // 2
    if len(normalized) % 2 == 0:
        left = normalized[:midpoint].strip()
        right = normalized[midpoint:].strip()
        if left and left.lower() == right.lower():
            return left
    words = normalized.split(" ")
    if len(words) % 2 == 0:
        half = len(words) // 2
        left_words = words[:half]
        right_words = words[half:]
        if [word.lower() for word in left_words] == [word.lower() for word in right_words]:
            return " ".join(left_words)
    return normalized


def _strip_card_prefix(description: str, title: str, company: str, location: str) -> str:
    cleaned = description
    patterns = [
        re.escape(_normalize_whitespace(title)),
        re.escape(_normalize_whitespace(company)),
        re.escape(_normalize_whitespace(location)),
    ]
    patterns = [pattern for pattern in patterns if pattern]
    if patterns:
        cleaned = re.sub(rf"^(?:{'|'.join(patterns)})+", "", cleaned, flags=re.IGNORECASE).strip(" -|·")
    cleaned = re.sub(
        r"\b(?:avaliando candidaturas|visualizado|promovida|promovido|há \d+ dias|candidatura simplificada|easy apply)\b",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    return _normalize_whitespace(cleaned).strip(" -|·")


def _looks_like_card_description(value: str) -> bool:
    normalized = value.lower()
    markers = ["candidatura simplificada", "avaliando candidaturas", "visualizado", "promovida", "há "]
    marker_hits = sum(1 for marker in markers if marker in normalized)
    return marker_hits >= 2 and len(normalized) < 220


def _infer_title_from_description(description: str) -> str:
    match = re.match(r"^([A-Z][A-Za-z0-9&/().,+\- ]{3,80})", description)
    if not match:
        return ""
    candidate = _normalize_whitespace(match.group(1))
    if candidate.lower().startswith("about the job"):
        return ""
    return candidate


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "")).strip()
