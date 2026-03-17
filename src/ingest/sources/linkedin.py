from __future__ import annotations

import re

from src.autopilot.linkedin_easy_apply import LinkedInPlaywrightRuntime
from src.core.config import Settings
from src.domain.models import CandidateProfile, JobPosting


def fetch_linkedin_jobs(settings: Settings, profile: CandidateProfile, limit: int = 10) -> list[JobPosting]:
    runtime = LinkedInPlaywrightRuntime(
        profile_dir=settings.browser_storage_dir / "linkedin",
        artifacts_dir=settings.artifacts_dir,
        headless=settings.playwright_headless,
    )
    try:
        raw_jobs = runtime.scrape_job_recommendations(
            keywords=profile.target_role,
            location=profile.location,
            limit=limit,
            easy_apply_only=True,
        )
    finally:
        runtime.close()

    jobs: list[JobPosting] = []
    for item in raw_jobs:
        if not _matches_profile_focus(profile, item):
            continue
        jobs.append(
            JobPosting(
                external_id=item["url"],
                source="linkedin",
                url=item["url"],
                title=item["title"],
                company=item["company"],
                location=item["location"],
                description=item["description"],
                requirements=[],
            )
        )
    return jobs


def _matches_profile_focus(profile: CandidateProfile, item: dict[str, str]) -> bool:
    haystack = " ".join(
        [
            item.get("title", ""),
            item.get("description", ""),
            item.get("location", ""),
        ]
    ).lower()
    target_tokens = [token for token in re.split(r"[^a-z0-9+#]+", profile.target_role.lower()) if len(token) >= 3]
    stack_tokens = [token for stack in profile.stacks for token in re.split(r"[^a-z0-9+#]+", stack.lower()) if len(token) >= 2]
    positive_tokens = list(dict.fromkeys(target_tokens + stack_tokens))
    if not positive_tokens:
        return True

    hit_count = sum(1 for token in positive_tokens if token and token in haystack)
    negative_markers = {
        "kyc",
        "compliance",
        "content reviewer",
        "content moderator",
        "sales",
        "recruiter",
        "customer support",
    }
    if any(marker in haystack for marker in negative_markers) and hit_count < 2:
        return False
    return hit_count >= 2 or any(token in (item.get("title", "").lower()) for token in target_tokens)
