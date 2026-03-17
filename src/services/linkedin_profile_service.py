from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

from src.autopilot.linkedin_easy_apply import LinkedInPlaywrightRuntime
from src.core.config import Settings
from src.domain.models import CandidateProfile, ExperienceItem, ProfileEvidence, ProfileMemoryItem
from src.domain.profile_loader import load_profile
from src.services.profile_brain_service import build_profile_brain_snapshot
from src.tracker.repo import TrackerRepository


def import_linkedin_profile(
    repo: TrackerRepository,
    settings: Settings,
    user_id: str,
    linkedin_url: str | None = None,
) -> dict[str, object]:
    stored = repo.get_profile(user_id=user_id)
    if stored is None:
        profile = load_profile(Path(settings.profile_path))
        repo.upsert_profile(profile.model_dump(), user_id=user_id)
    else:
        profile = CandidateProfile.model_validate_json(stored.profile_json)

    source_url = (linkedin_url or profile.links.get("linkedin") or "").strip()
    normalized_url = _normalize_linkedin_url(source_url)
    if not normalized_url:
        raise ValueError("Nenhum perfil LinkedIn valido foi encontrado no Profile Brain.")

    runtime = LinkedInPlaywrightRuntime(
        profile_dir=settings.browser_storage_dir / "linkedin",
        artifacts_dir=settings.artifacts_dir,
        headless=settings.playwright_headless,
    )
    try:
        raw = runtime.scrape_profile(normalized_url)
    except RuntimeError as exc:
        if str(exc) == "playwright_not_installed":
            raise ValueError("Playwright nao esta instalado no ambiente Python.") from exc
        raise
    finally:
        runtime.close()

    if raw["status"] == "paused":
        raise ValueError(str(raw.get("recommended_action") or raw["summary"]))

    payload = raw.get("data", {})
    enriched_profile, evidences, memories = _merge_linkedin_into_profile(profile, normalized_url, payload)

    repo.upsert_profile(enriched_profile.model_dump(), user_id=user_id)
    for evidence in evidences:
        repo.create_profile_evidence(
            evidence_id=evidence.id,
            kind=evidence.kind,
            title=evidence.title,
            content=evidence.content,
            source=evidence.source,
            user_id=user_id,
        )
    for memory in memories:
        repo.upsert_profile_memory_item(
            memory_id=memory.id,
            kind=memory.kind,
            title=memory.title,
            content=memory.content,
            confidence=memory.confidence,
            source=memory.source,
            user_id=user_id,
        )
    repo.create_profile_conversation_turn(
        turn_id=str(uuid4()),
        role="assistant",
        message="Importei evidencias do seu LinkedIn e atualizei resumo, experiencias e memoria profissional.",
        user_id=user_id,
    )
    return {
        "assistant_message": "Li seu LinkedIn com a sessao autenticada e consolidei headline, experiencias e sinais profissionais no Profile Brain.",
        "brain": build_profile_brain_snapshot(repo, enriched_profile, user_id),
        "linkedin_url": normalized_url,
    }


def _merge_linkedin_into_profile(
    profile: CandidateProfile,
    linkedin_url: str,
    payload: object,
) -> tuple[CandidateProfile, list[ProfileEvidence], list[ProfileMemoryItem]]:
    data = payload if isinstance(payload, dict) else {}
    name = _prefer_non_empty(str(data.get("name", "")), profile.name)
    headline = str(data.get("headline", "")).strip()
    location = _prefer_non_empty(str(data.get("location", "")), profile.location)
    about = str(data.get("about", "")).strip()
    experiences_data = data.get("experiences", [])

    merged_experiences = list(profile.experiences)
    seen_keys = {item.company.lower(): item for item in merged_experiences}
    evidences: list[ProfileEvidence] = []
    memories: list[ProfileMemoryItem] = []

    if headline:
        memories.append(
            ProfileMemoryItem(
                id=str(uuid4()),
                kind="headline",
                title="Headline do LinkedIn",
                content=headline,
                confidence=0.88,
                source="linkedin",
            )
        )
        evidences.append(
            ProfileEvidence(
                id=str(uuid4()),
                kind="linkedin_headline",
                title="Headline importada do LinkedIn",
                content=headline,
                source="linkedin",
            )
        )

    if about:
        memories.append(
            ProfileMemoryItem(
                id=str(uuid4()),
                kind="summary",
                title="Resumo profissional do LinkedIn",
                content=about[:1000],
                confidence=0.82,
                source="linkedin",
            )
        )
        evidences.append(
            ProfileEvidence(
                id=str(uuid4()),
                kind="linkedin_about",
                title="Sobre importado do LinkedIn",
                content=about[:1500],
                source="linkedin",
            )
        )

    if location:
        memories.append(
            ProfileMemoryItem(
                id=str(uuid4()),
                kind="preference",
                title="Localizacao observada no LinkedIn",
                content=location,
                confidence=0.74,
                source="linkedin",
            )
        )
        evidences.append(
            ProfileEvidence(
                id=str(uuid4()),
                kind="linkedin_location",
                title="Localizacao importada do LinkedIn",
                content=location,
                source="linkedin",
            )
        )

    if isinstance(experiences_data, list):
        for entry in experiences_data:
            if not isinstance(entry, list) or not entry:
                continue
            title_company = str(entry[0]).strip()
            period = str(entry[1]).strip() if len(entry) > 1 else ""
            bullets = [str(item).strip() for item in entry[2:5] if str(item).strip()]
            if not title_company:
                continue
            key = title_company.lower()
            if key not in seen_keys:
                merged_experiences.append(
                    ExperienceItem(
                        company=title_company,
                        period=period,
                        bullets=bullets or ["Experiencia importada do LinkedIn."],
                    )
                )
                seen_keys[key] = merged_experiences[-1]
            evidences.append(
                ProfileEvidence(
                    id=str(uuid4()),
                    kind="linkedin_experience",
                    title=f"Experiencia LinkedIn: {title_company}",
                    content=" | ".join([part for part in [period, *bullets] if part])[:1500],
                    source="linkedin",
                )
            )

    links = dict(profile.links)
    links["linkedin"] = linkedin_url
    updated_preferences = dict(profile.preferences)
    if headline:
        updated_preferences["linkedin_headline"] = headline

    updated_profile = CandidateProfile(
        name=name,
        target_role=_prefer_non_empty(headline, profile.target_role),
        location=location,
        stacks=profile.stacks,
        links=links,
        experiences=merged_experiences,
        projects=profile.projects,
        education=profile.education,
        preferences=updated_preferences,
        bullet_bank=profile.bullet_bank,
        learning_plan=profile.learning_plan,
    )
    return updated_profile, evidences, memories


def _normalize_linkedin_url(url_or_handle: str) -> str | None:
    text = url_or_handle.strip().rstrip("/")
    if not text:
        return None
    if "linkedin.com" not in text.lower():
        handle = text.lstrip("@")
        return f"https://www.linkedin.com/in/{handle}"
    parsed = urlparse(text if "://" in text else f"https://{text}")
    if "linkedin.com" not in parsed.netloc.lower():
        return None
    parts = [part for part in parsed.path.split("/") if part]
    if not parts:
        return None
    return f"https://www.linkedin.com/{'/'.join(parts)}"


def _prefer_non_empty(candidate: str, fallback: str) -> str:
    return candidate.strip() or fallback
