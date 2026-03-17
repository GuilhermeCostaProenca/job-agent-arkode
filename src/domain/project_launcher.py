from __future__ import annotations

from pathlib import Path

from src.core.utils import safe_filename_token
from src.domain.models import CandidateProfile, JobAnchors, JobPosting


def generate_project_prompt(job: JobPosting, anchors: JobAnchors, profile: CandidateProfile) -> str:
    return (
        f"# Project prompt for {job.title}\n\n"
        f"Company: {job.company}\n"
        f"Location: {job.location}\n"
        f"Top skills: {', '.join(anchors.top_skills[:8])}\n\n"
        f"Build a concrete portfolio-ready project that proves fit for {profile.target_role} roles.\n"
        f"Use stacks close to: {', '.join(profile.stacks[:6])}\n\n"
        "## User stories\n"
        "- Como recrutador, quero ver um projeto que demonstre aderencia real a vaga.\n"
        "- Como avaliador tecnico, quero enxergar estrutura, clareza e criterio de entrega.\n\n"
        "## Estrutura de pastas\n"
        "- app/\n"
        "- domain/\n"
        "- infra/\n"
        "- tests/\n"
    )


def write_project_prompt(
    artifacts_dir: Path,
    job: JobPosting,
    anchors: JobAnchors,
    profile: CandidateProfile,
) -> str:
    token = safe_filename_token(job.external_id)
    path = artifacts_dir / f"project_prompt_{token}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(generate_project_prompt(job, anchors, profile), encoding="utf-8")
    return str(path)
