from __future__ import annotations

from pathlib import Path

from src.domain.models import CandidateProfile, JobAnchors, JobPosting


def generate_project_prompt(job: JobPosting, anchors: JobAnchors, profile: CandidateProfile) -> str:
    skills = anchors.top_skills[:4] or profile.stacks[:4]
    project_name = f"SkillProof {job.company} {job.title}"[:80]
    stack = ", ".join(skills)
    stories = "\n".join(
        [
            "- Como recrutador, quero ver evidências práticas das skills-chave.",
            "- Como usuário, quero fluxo claro de ponta a ponta com dados reais/mock.",
            "- Como time técnico, quero README com setup e testes.",
        ]
    )
    return (
        f"# Mini Projeto: {project_name}\n\n"
        "## Problema que resolve\n"
        f"Demonstrar aderência prática à vaga {job.title} ({job.company}).\n\n"
        f"## Stack sugerida\n{stack}\n\n"
        f"## User stories\n{stories}\n\n"
        "## Estrutura de pastas\n"
        "- src/\n- tests/\n- docs/\n- README.md\n\n"
        "## Prompt pronto para Codex\n"
        f"Construa um mini projeto em {stack} que simule um cenário real da vaga {job.title}. "
        "Inclua API/fluxo principal, testes automatizados, lint, "
        "documentação e instruções de execução."
    )


def write_project_prompt(
    artifacts_dir: Path,
    job: JobPosting,
    anchors: JobAnchors,
    profile: CandidateProfile,
) -> str:
    path = artifacts_dir / f"project_prompt_{job.external_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(generate_project_prompt(job, anchors, profile), encoding="utf-8")
    return str(path)
