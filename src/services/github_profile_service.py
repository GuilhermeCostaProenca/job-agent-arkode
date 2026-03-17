from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import httpx

from src.core.config import Settings
from src.domain.models import CandidateProfile, ProfileEvidence, ProfileMemoryItem, ProjectItem
from src.domain.profile_loader import load_profile
from src.services.profile_brain_service import build_profile_brain_snapshot
from src.tracker.repo import TrackerRepository


@dataclass(slots=True)
class GitHubRepo:
    name: str
    html_url: str
    description: str
    language: str
    topics: list[str]
    stargazers_count: int
    fork: bool
    pushed_at: str


def import_github_profile(
    repo: TrackerRepository,
    settings: Settings,
    user_id: str,
    github_url: str | None = None,
) -> dict[str, object]:
    stored = repo.get_profile(user_id=user_id)
    if stored is None:
        profile = load_profile(Path(settings.profile_path))
        repo.upsert_profile(profile.model_dump(), user_id=user_id)
    else:
        profile = CandidateProfile.model_validate_json(stored.profile_json)

    source_url = (github_url or profile.links.get("github") or "").strip()
    username = _extract_github_username(source_url)
    if not username:
        raise ValueError("Nenhum perfil GitHub valido foi encontrado no Profile Brain.")

    repos = _fetch_repositories(settings, username)
    enriched_profile, evidences, memories = _merge_github_into_profile(profile, username, repos)

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
        message=f"Importei evidencias do GitHub de @{username} e atualizei projetos, stacks e memorias do seu perfil.",
        user_id=user_id,
    )
    return {
        "assistant_message": f"Importei o GitHub de @{username} e consolidei o que parece mais relevante para a sua narrativa profissional atual.",
        "brain": build_profile_brain_snapshot(repo, enriched_profile, user_id),
        "imported_repositories": len(repos),
        "github_username": username,
    }


def _fetch_repositories(settings: Settings, username: str) -> list[GitHubRepo]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "job-agent-arkode",
    }
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"

    with httpx.Client(timeout=30.0, headers=headers) as client:
        response = client.get(
            f"https://api.github.com/users/{username}/repos",
            params={"per_page": 12, "sort": "updated", "direction": "desc"},
        )
        response.raise_for_status()
        payload = response.json()

    repos: list[GitHubRepo] = []
    for item in payload:
        if item.get("fork"):
            continue
        repos.append(
            GitHubRepo(
                name=str(item.get("name", "")),
                html_url=str(item.get("html_url", "")),
                description=str(item.get("description") or ""),
                language=str(item.get("language") or ""),
                topics=[str(topic) for topic in item.get("topics", [])],
                stargazers_count=int(item.get("stargazers_count", 0)),
                fork=bool(item.get("fork", False)),
                pushed_at=str(item.get("pushed_at") or ""),
            )
        )
    repos.sort(key=lambda item: (item.stargazers_count, item.pushed_at), reverse=True)
    return repos[:6]


def _merge_github_into_profile(
    profile: CandidateProfile,
    username: str,
    repos: list[GitHubRepo],
) -> tuple[CandidateProfile, list[ProfileEvidence], list[ProfileMemoryItem]]:
    existing_project_names = {project.name.lower() for project in profile.projects}
    merged_projects = list(profile.projects)
    stack_counter = Counter(stack for stack in profile.stacks)
    evidences: list[ProfileEvidence] = []
    memories: list[ProfileMemoryItem] = []

    for gh_repo in repos:
        repo_stack = _repo_stack(gh_repo)
        for stack in repo_stack:
            stack_counter[stack] += 1
        if gh_repo.name.lower() not in existing_project_names:
            merged_projects.append(
                ProjectItem(
                    name=gh_repo.name,
                    description=gh_repo.description or f"Repositorio importado do GitHub de @{username}.",
                    stack=repo_stack,
                    links=[gh_repo.html_url],
                )
            )
            existing_project_names.add(gh_repo.name.lower())

        evidence_text = gh_repo.description or f"Repositorio {gh_repo.name} com stack {', '.join(repo_stack) if repo_stack else 'nao identificada'}."
        evidences.append(
            ProfileEvidence(
                id=str(uuid4()),
                kind="github_repo",
                title=f"GitHub repo: {gh_repo.name}",
                content=evidence_text,
                source="github",
            )
        )
        memories.append(
            ProfileMemoryItem(
                id=str(uuid4()),
                kind="project",
                title=f"Projeto importado: {gh_repo.name}",
                content=evidence_text,
                confidence=0.82,
                source="github",
            )
        )

    dominant_stacks = [stack for stack, _count in stack_counter.most_common(12)]
    if dominant_stacks:
        memories.append(
            ProfileMemoryItem(
                id=str(uuid4()),
                kind="skill",
                title="Stacks inferidas do GitHub",
                content=", ".join(dominant_stacks[:6]),
                confidence=0.76,
                source="github",
            )
        )

    links = dict(profile.links)
    links["github"] = profile.links.get("github") or f"https://github.com/{username}"
    updated = CandidateProfile(
        name=profile.name,
        target_role=profile.target_role,
        location=profile.location,
        stacks=dominant_stacks or profile.stacks,
        links=links,
        experiences=profile.experiences,
        projects=merged_projects,
        education=profile.education,
        preferences=profile.preferences,
        bullet_bank=profile.bullet_bank,
        learning_plan=profile.learning_plan,
    )
    return updated, evidences, memories


def _repo_stack(repo: GitHubRepo) -> list[str]:
    ordered = []
    if repo.language:
        ordered.append(repo.language)
    for topic in repo.topics:
        normalized = topic.replace("-", " ").strip()
        if normalized and normalized.lower() not in {item.lower() for item in ordered}:
            ordered.append(normalized.title())
    return ordered[:5]


def _extract_github_username(url_or_username: str) -> str | None:
    text = url_or_username.strip().rstrip("/")
    if not text:
        return None
    if "/" not in text and "github.com" not in text.lower():
        return text.lstrip("@")
    parsed = urlparse(text if "://" in text else f"https://{text}")
    if "github.com" not in parsed.netloc.lower():
        return None
    parts = [part for part in parsed.path.split("/") if part]
    return parts[0] if parts else None
