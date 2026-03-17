from __future__ import annotations

import json
import re
from pathlib import Path
from uuid import uuid4

import httpx

from src.core.config import Settings
from src.domain.models import CandidateProfile, ProfileBrainSnapshot, ProfileConflict, ProfileConversationTurn, ProfileEvidence, ProfileMemoryItem
from src.domain.profile_loader import load_profile
from src.tracker.repo import TrackerRepository


def get_profile_brain(repo: TrackerRepository, profile_path: Path, user_id: str) -> ProfileBrainSnapshot:
    stored = repo.get_profile(user_id=user_id)
    if stored is None:
        profile = load_profile(profile_path)
        repo.upsert_profile(profile.model_dump(), user_id=user_id)
    else:
        profile = CandidateProfile.model_validate_json(stored.profile_json)
    return build_profile_brain_snapshot(repo, profile, user_id)


def get_effective_profile(repo: TrackerRepository, profile_path: Path, user_id: str) -> CandidateProfile:
    stored = repo.get_profile(user_id=user_id)
    if stored is None:
        profile = load_profile(profile_path)
        repo.upsert_profile(profile.model_dump(), user_id=user_id)
    else:
        profile = CandidateProfile.model_validate_json(stored.profile_json)
    return _apply_confirmations_to_profile(profile, _confirmed_values(_list_memory(repo, user_id)))


def chat_with_profile_brain(repo: TrackerRepository, settings: Settings, message: str, user_id: str) -> dict[str, object]:
    brain = get_profile_brain(repo, settings.profile_path, user_id)
    repo.create_profile_conversation_turn(str(uuid4()), "user", message, user_id=user_id)
    update = _generate_profile_update(settings, brain.profile, message)
    updated_profile = _apply_profile_update(brain.profile, update)
    repo.upsert_profile(updated_profile.model_dump(), user_id=user_id)

    new_memories = _build_memory_items(update, message)
    for memory in new_memories:
        repo.upsert_profile_memory_item(
            memory_id=memory.id,
            kind=memory.kind,
            title=memory.title,
            content=memory.content,
            confidence=memory.confidence,
            source=memory.source,
            user_id=user_id,
        )
    if message.strip():
        repo.create_profile_evidence(
            evidence_id=str(uuid4()),
            kind="conversation_note",
            title="Conversational profile update",
            content=message,
            source="chat",
            user_id=user_id,
        )

    assistant_message = update["assistant_message"]
    repo.create_profile_conversation_turn(str(uuid4()), "assistant", assistant_message, user_id=user_id)
    refreshed = get_profile_brain(repo, settings.profile_path, user_id)
    return {
        "assistant_message": assistant_message,
        "brain": refreshed,
    }


def resolve_profile_conflict(
    repo: TrackerRepository,
    settings: Settings,
    user_id: str,
    field: str,
    chosen_value: str,
) -> dict[str, object]:
    stored = repo.get_profile(user_id=user_id)
    if stored is None:
        profile = load_profile(settings.profile_path)
    else:
        profile = CandidateProfile.model_validate_json(stored.profile_json)

    normalized_field = field.strip()
    normalized_value = chosen_value.strip()
    if not normalized_field or not normalized_value:
        raise ValueError("field and chosen_value are required")

    updated_profile = _apply_confirmed_value(profile, normalized_field, normalized_value)
    repo.upsert_profile(updated_profile.model_dump(), user_id=user_id)
    repo.upsert_profile_memory_item(
        memory_id=str(uuid4()),
        kind="confirmation",
        title=f"Confirmed {normalized_field}",
        content=normalized_value,
        confidence=1.0,
        source="user_confirmed",
        user_id=user_id,
    )
    repo.create_profile_evidence(
        evidence_id=str(uuid4()),
        kind="user_confirmation",
        title=f"Confirmacao manual: {normalized_field}",
        content=normalized_value,
        source="user_confirmed",
        user_id=user_id,
    )
    repo.create_profile_conversation_turn(
        str(uuid4()),
        "assistant",
        f"Confirmei {normalized_field} como '{normalized_value}' e vou usar isso como referencia prioritaria nas proximas decisoes.",
        user_id=user_id,
    )
    return {
        "assistant_message": f"Vou tratar '{normalized_value}' como valor confirmado para {normalized_field}.",
        "brain": build_profile_brain_snapshot(repo, updated_profile, user_id),
    }


def build_profile_brain_snapshot(repo: TrackerRepository, profile: CandidateProfile, user_id: str) -> ProfileBrainSnapshot:
    evidences = _list_evidences(repo, user_id)
    memory_items = _list_memory(repo, user_id)
    conversation = _list_conversation(repo, user_id)
    return ProfileBrainSnapshot(
        profile=profile,
        evidences=evidences,
        memory_items=memory_items,
        conversation=conversation,
        conflicts=_detect_conflicts(profile, evidences, memory_items),
    )


def _generate_profile_update(settings: Settings, profile: CandidateProfile, message: str) -> dict[str, object]:
    if settings.llm_enabled and settings.gemini_api_key:
        try:
            return _generate_profile_update_with_gemini(settings, profile, message)
        except Exception:
            pass
    return _fallback_profile_update(profile, message)


def _generate_profile_update_with_gemini(settings: Settings, profile: CandidateProfile, message: str) -> dict[str, object]:
    prompt = (
        "You are a profile brain updater for a job agent. "
        "Return JSON only with keys assistant_message, target_role, location, stacks, learning_plan, preferences_updates, memory_items. "
        "memory_items must be a list of objects with kind, title, content, confidence. "
        "Only update fields when the message supports it. "
        f"CURRENT_PROFILE={json.dumps(profile.model_dump(), ensure_ascii=False)} "
        f"USER_MESSAGE={json.dumps(message, ensure_ascii=False)}"
    )
    response = httpx.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent",
        params={"key": settings.gemini_api_key},
        headers={"Content-Type": "application/json"},
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0.3},
        },
        timeout=45.0,
    )
    response.raise_for_status()
    text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
    parsed = json.loads(text)
    return {
        "assistant_message": parsed.get("assistant_message", "Atualizei seu perfil com base na conversa."),
        "target_role": parsed.get("target_role") or profile.target_role,
        "location": parsed.get("location") or profile.location,
        "stacks": [str(item) for item in parsed.get("stacks", [])] or profile.stacks,
        "learning_plan": [str(item) for item in parsed.get("learning_plan", [])] or profile.learning_plan,
        "preferences_updates": parsed.get("preferences_updates", {}) or {},
        "memory_items": parsed.get("memory_items", []) or [],
    }


def _fallback_profile_update(profile: CandidateProfile, message: str) -> dict[str, object]:
    lowered = message.lower()
    target_role = profile.target_role
    location = profile.location
    stacks = list(profile.stacks)
    learning_plan = list(profile.learning_plan)
    preferences_updates: dict[str, object] = {}
    memory_items: list[dict[str, object]] = []

    role_match = re.search(r"\b(estagio|junior|j[uú]nior|pleno|senior)\b", lowered)
    if role_match:
        target_role = role_match.group(1)
        memory_items.append({"kind": "goal", "title": "Senioridade alvo", "content": target_role, "confidence": 0.9})

    if any(term in lowered for term in ["remoto", "remota", "hibrido", "hibrida", "presencial"]):
        location = message
        memory_items.append({"kind": "preference", "title": "Localizacao desejada", "content": message, "confidence": 0.7})

    for skill in ["python", "fastapi", "java", "react", "flutter", "kotlin", "sql", "power bi"]:
        if skill in lowered and skill.title() not in stacks:
            stacks.append(skill.title())
            memory_items.append({"kind": "skill", "title": f"Interesse em {skill.title()}", "content": message, "confidence": 0.65})

    if "projeto" in lowered:
        memory_items.append({"kind": "project", "title": "Projeto citado em conversa", "content": message, "confidence": 0.8})

    if "nao quero" in lowered or "não quero" in lowered:
        preferences_updates["no_go"] = message
        memory_items.append({"kind": "constraint", "title": "Restricao declarada", "content": message, "confidence": 0.85})

    if "quero aprender" in lowered or "aprender" in lowered:
        learning_plan.append(message)
        memory_items.append({"kind": "learning_goal", "title": "Objetivo de aprendizado", "content": message, "confidence": 0.75})

    return {
        "assistant_message": "Atualizei a memoria do seu perfil com base no que voce acabou de me contar.",
        "target_role": target_role,
        "location": location,
        "stacks": stacks,
        "learning_plan": learning_plan,
        "preferences_updates": preferences_updates,
        "memory_items": memory_items,
    }


def _apply_profile_update(profile: CandidateProfile, update: dict[str, object]) -> CandidateProfile:
    merged_preferences = {**profile.preferences, **dict(update.get("preferences_updates", {}))}
    return CandidateProfile(
        name=profile.name,
        target_role=str(update.get("target_role", profile.target_role)),
        location=str(update.get("location", profile.location)),
        stacks=list(dict.fromkeys([str(item) for item in update.get("stacks", profile.stacks)])),
        links=profile.links,
        experiences=profile.experiences,
        projects=profile.projects,
        education=profile.education,
        preferences=merged_preferences,
        bullet_bank=profile.bullet_bank,
        learning_plan=list(dict.fromkeys([str(item) for item in update.get("learning_plan", profile.learning_plan)])),
    )


def _apply_confirmed_value(profile: CandidateProfile, field: str, chosen_value: str) -> CandidateProfile:
    if field == "target_role":
        return profile.model_copy(update={"target_role": chosen_value})
    if field == "location":
        return profile.model_copy(update={"location": chosen_value})
    if field == "stacks":
        stacks = [item.strip() for item in chosen_value.split(",") if item.strip()]
        return profile.model_copy(update={"stacks": list(dict.fromkeys(stacks)) or profile.stacks})
    preferences = dict(profile.preferences)
    preferences[field] = chosen_value
    return profile.model_copy(update={"preferences": preferences})


def _apply_confirmations_to_profile(profile: CandidateProfile, confirmed: dict[str, str]) -> CandidateProfile:
    effective = profile
    for field, chosen_value in confirmed.items():
        effective = _apply_confirmed_value(effective, field, chosen_value)
    return effective


def _build_memory_items(update: dict[str, object], message: str) -> list[ProfileMemoryItem]:
    items = update.get("memory_items", [])
    out: list[ProfileMemoryItem] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        out.append(
            ProfileMemoryItem(
                id=str(uuid4()),
                kind=str(item.get("kind", "note")),
                title=str(item.get("title", "Profile memory")),
                content=str(item.get("content", message)),
                confidence=float(item.get("confidence", 0.6)),
                source="chat",
            )
        )
    return out


def _list_evidences(repo: TrackerRepository, user_id: str) -> list[ProfileEvidence]:
    return [
        ProfileEvidence(
            id=row.id,
            kind=row.kind,
            title=row.title,
            content=row.content,
            source=row.source,
            created_at=row.created_at,
        )
        for row in repo.list_profile_evidence(user_id=user_id)
    ]


def _list_memory(repo: TrackerRepository, user_id: str) -> list[ProfileMemoryItem]:
    return [
        ProfileMemoryItem(
            id=row.id,
            kind=row.kind,
            title=row.title,
            content=row.content,
            confidence=row.confidence,
            source=row.source,
            updated_at=row.updated_at,
        )
        for row in repo.list_profile_memory_items(user_id=user_id)
    ]


def _list_conversation(repo: TrackerRepository, user_id: str) -> list[ProfileConversationTurn]:
    return [
        ProfileConversationTurn(id=row.id, role=row.role, message=row.message, created_at=row.created_at)
        for row in repo.list_profile_conversation(user_id=user_id)
    ]


def _detect_conflicts(
    profile: CandidateProfile,
    evidences: list[ProfileEvidence],
    memory_items: list[ProfileMemoryItem],
) -> list[ProfileConflict]:
    conflicts: list[ProfileConflict] = []
    confirmed = _confirmed_values(memory_items)
    conflicts.extend(_detect_goal_conflict(profile, memory_items, confirmed))
    conflicts.extend(_detect_location_conflict(profile, memory_items, evidences, confirmed))
    conflicts.extend(_detect_stack_conflict(profile, memory_items, confirmed))
    return conflicts


def _detect_goal_conflict(profile: CandidateProfile, memory_items: list[ProfileMemoryItem], confirmed: dict[str, str]) -> list[ProfileConflict]:
    goal_values = _collect_values(memory_items, kinds={"goal", "headline"}, title_terms=("senioridade", "headline"))
    normalized_profile_goal = _normalize_text(profile.target_role)
    unique_values = _unique_non_empty(goal_values + ([profile.target_role] if normalized_profile_goal else []))
    if _normalize_text(confirmed.get("target_role", "")) == normalized_profile_goal:
        return []
    if len(unique_values) < 2:
        return []
    return [
        ProfileConflict(
            id=f"goal:{hash('|'.join(unique_values))}",
            field="target_role",
            summary="Existem sinais diferentes sobre o foco ou senioridade atual.",
            recommended_action="Confirme qual objetivo deve guiar descoberta e candidatura agora.",
            values=unique_values,
            sources=_unique_non_empty([item.source for item in memory_items if item.kind in {"goal", "headline"}] + ["profile"]),
            confidence=0.78,
        )
    ]


def _detect_location_conflict(
    profile: CandidateProfile,
    memory_items: list[ProfileMemoryItem],
    evidences: list[ProfileEvidence],
    confirmed: dict[str, str],
) -> list[ProfileConflict]:
    values = [profile.location]
    values.extend(item.content for item in memory_items if item.kind == "preference")
    values.extend(evidence.content for evidence in evidences if evidence.kind in {"conversation_note", "linkedin_headline"} and any(term in evidence.content.lower() for term in ["remoto", "hibrido", "presencial"]))
    unique_values = _unique_non_empty(values)
    if _normalize_text(confirmed.get("location", "")) == _normalize_text(profile.location):
        return []
    if len(unique_values) < 2:
        return []
    return [
        ProfileConflict(
            id=f"location:{hash('|'.join(unique_values))}",
            field="location",
            summary="As preferencias de localizacao ainda estao ambiguas entre fontes recentes.",
            recommended_action="Escolha se o foco atual eh remoto, hibrido, presencial ou uma combinacao clara.",
            values=unique_values,
            sources=_unique_non_empty(["profile"] + [item.source for item in memory_items if item.kind == "preference"]),
            confidence=0.72,
        )
    ]


def _detect_stack_conflict(profile: CandidateProfile, memory_items: list[ProfileMemoryItem], confirmed: dict[str, str]) -> list[ProfileConflict]:
    inferred_skill_sets = [
        {part.strip() for part in item.content.split(",") if part.strip()}
        for item in memory_items
        if item.kind == "skill"
    ]
    if not inferred_skill_sets:
        return []
    profile_stacks = {_normalize_text(stack) for stack in profile.stacks if stack.strip()}
    confirmed_stacks = {_normalize_text(item) for item in confirmed.get("stacks", "").split(",") if item.strip()}
    if confirmed_stacks and confirmed_stacks == profile_stacks:
        return []
    divergent_values: list[str] = []
    for skill_set in inferred_skill_sets:
        normalized_set = {_normalize_text(item) for item in skill_set if item}
        if normalized_set and normalized_set != profile_stacks:
            divergent_values.append(", ".join(sorted(skill_set)))
    if not divergent_values:
        return []
    values = _unique_non_empty([", ".join(profile.stacks), *divergent_values])
    if len(values) < 2:
        return []
    return [
        ProfileConflict(
            id=f"stacks:{hash('|'.join(values))}",
            field="stacks",
            summary="As stacks priorizadas do perfil diferem do que foi inferido pelas fontes externas.",
            recommended_action="Revise quais stacks devem ser tratadas como foco atual e quais sao apenas historico.",
            values=values,
            sources=_unique_non_empty(["profile"] + [item.source for item in memory_items if item.kind == "skill"]),
            confidence=0.7,
        )
    ]


def _collect_values(
    memory_items: list[ProfileMemoryItem],
    *,
    kinds: set[str],
    title_terms: tuple[str, ...] = (),
) -> list[str]:
    values: list[str] = []
    for item in memory_items:
        normalized_title = _normalize_text(item.title)
        if item.kind in kinds or any(term in normalized_title for term in title_terms):
            values.append(item.content)
    return values


def _confirmed_values(memory_items: list[ProfileMemoryItem]) -> dict[str, str]:
    confirmed: dict[str, str] = {}
    for item in memory_items:
        if item.kind != "confirmation":
            continue
        normalized_title = _normalize_text(item.title)
        if normalized_title.startswith("confirmed "):
            field = item.title[len("Confirmed ") :].strip()
            if field:
                confirmed[field] = item.content
    return confirmed


def _unique_non_empty(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        stripped = value.strip()
        normalized = _normalize_text(stripped)
        if not stripped or normalized in seen:
            continue
        seen.add(normalized)
        out.append(stripped)
    return out


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())
