from __future__ import annotations

from pathlib import Path

from jinja2 import Template

from src.domain.models import ArtifactBundle, CandidateProfile, JobPosting

RESUME_TEMPLATE = """# {{ profile.name }}

**Objetivo:** {{ profile.target_role }}

## Stack principal
{% for stack in profile.stacks %}- {{ stack }}
{% endfor %}

## Experiência relevante para {{ job.title }} na {{ job.company }}
{% for exp in profile.experiences %}
### {{ exp.company }} ({{ exp.period }})
{% for bullet in exp.bullets %}- {{ bullet }}
{% endfor %}
{% endfor %}

## Projetos
{% for project in profile.projects %}
- **{{ project.name }}**: {{ project.description }} ({{ ', '.join(project.stack) }})
{% endfor %}

## Educação
{% for item in profile.education %}- {{ item }}
{% endfor %}
"""

COVER_TEMPLATE = """# Apresentação {{ tone }}

Olá time da {{ job.company }},

Tenho interesse na vaga **{{ job.title }}**.
Minha experiência com {{ highlighted_skills }} me permite contribuir desde o início.

{% if tone == 'curto' %}
Estou pronto para aprender rápido, executar com qualidade e colaborar com o time.
{% elif tone == 'medio' %}
Já apliquei essas tecnologias em projetos e experiências práticas.
Onde houver gaps, estou em aprendizagem ativa e consigo evoluir rápido.
{% else %}
Quero construir soluções com impacto real no negócio,
combinando execução técnica com visão de produto e dados.
{% endif %}

Obrigado pelo tempo!
"""

CHECKLIST_TEMPLATE = """# Checklist de aplicação - {{ job.company }} / {{ job.title }}

## Requisitos atendidos
{% for req in met %}- [x] {{ req }}
{% endfor %}

## Gaps e plano
{% for gap in gaps %}- [ ] {{ gap }} (em aprendizagem / experiência em projetos)
{% endfor %}

## Perguntas comuns
- Por que você quer esta vaga?
- Qual projeto melhor demonstra aderência ao stack?
- Como você aprende rápido quando há gaps?
"""


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_artifacts(
    job: JobPosting, profile: CandidateProfile, artifacts_dir: Path
) -> ArtifactBundle:
    skills_lower = {s.lower() for s in profile.stacks}
    reqs = job.requirements or [job.description]
    met = [req for req in reqs if any(skill in req.lower() for skill in skills_lower)]
    gaps = [req for req in reqs if req not in met]
    highlighted = ", ".join(profile.stacks[:4])

    resume_path = artifacts_dir / f"resume_{job.external_id}.md"
    _write(resume_path, Template(RESUME_TEMPLATE).render(profile=profile, job=job))

    cover_paths: list[str] = []
    for tone in ["curto", "medio", "visionario"]:
        cover_path = artifacts_dir / f"cover_{tone}_{job.external_id}.md"
        _write(
            cover_path,
            Template(COVER_TEMPLATE).render(
                profile=profile,
                job=job,
                tone=tone,
                highlighted_skills=highlighted,
            ),
        )
        cover_paths.append(str(cover_path))

    dm_path = artifacts_dir / f"outreach_dm_{job.external_id}.txt"
    _write(
        dm_path,
        (
            f"Oi! Vi a vaga {job.title} na {job.company}. Tenho experiência com {highlighted} "
            "e projetos alinhados. Posso compartilhar mais detalhes e CV adaptado."
        ),
    )

    email_path = artifacts_dir / f"outreach_email_{job.external_id}.txt"
    _write(
        email_path,
        (
            f"Assunto: Candidatura - {job.title}\n\n"
            "Prezados,\n\n"
            f"Tenho interesse na vaga {job.title} e experiência prática com {highlighted}. "
            "Posso contribuir com execução e evolução contínua.\n\n"
            "Atenciosamente."
        ),
    )

    checklist_path = artifacts_dir / f"application_checklist_{job.external_id}.md"
    _write(checklist_path, Template(CHECKLIST_TEMPLATE).render(job=job, met=met, gaps=gaps))

    return ArtifactBundle(
        resume_path=str(resume_path),
        cover_paths=cover_paths,
        dm_path=str(dm_path),
        email_path=str(email_path),
        checklist_path=str(checklist_path),
    )
