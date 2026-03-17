from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from src.domain.models import CandidateProfile, ProfileEvidence, ProfileSnapshot
from src.domain.profile_loader import load_profile
from src.tracker.repo import TrackerRepository


def get_profile_snapshot(repo: TrackerRepository, profile_path: Path, user_id: str) -> ProfileSnapshot:
    stored = repo.get_profile(user_id=user_id)
    if stored is None:
        profile = load_profile(profile_path)
        repo.upsert_profile(profile.model_dump(), user_id=user_id)
    else:
        profile = CandidateProfile.model_validate_json(stored.profile_json)
    evidences = [
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
    return ProfileSnapshot(profile=profile, evidences=evidences)


def save_profile_snapshot(repo: TrackerRepository, snapshot: ProfileSnapshot, user_id: str) -> ProfileSnapshot:
    repo.upsert_profile(snapshot.profile.model_dump(), user_id=user_id)
    repo.clear_profile_evidence(user_id=user_id)
    for evidence in snapshot.evidences:
        repo.create_profile_evidence(
            evidence_id=evidence.id or str(uuid4()),
            kind=evidence.kind,
            title=evidence.title,
            content=evidence.content,
            source=evidence.source,
            user_id=user_id,
        )
    return ProfileSnapshot(profile=snapshot.profile, evidences=repo_snapshot_evidence(repo, user_id=user_id))


def repo_snapshot_evidence(repo: TrackerRepository, user_id: str) -> list[ProfileEvidence]:
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
