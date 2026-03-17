from __future__ import annotations

import json
from pathlib import Path

from jinja2 import Template

from src.core.utils import safe_filename_token
from src.domain.models import ArtifactBundle, CandidateProfile, JobAnchors, JobPosting, ScoringResult
from src.domain.project_launcher import write_project_prompt
from src.domain.scoring import recommendation_from_score

RESUME_TEMPLATE = """# {{ profile.name }}

## Resumo direcionado
{{ summary_lines[0] }}
{{ summary_lines[1] }}
{{ summary_lines[2] }}

## Stack foco da vaga
{% for stack in focus_skills %}- {{ stack }}
{% endfor %}

## Experiencias relevantes
{% for exp in ranked_experiences %}
### {{ exp.company }} ({{ exp.period }})
{% for bullet in exp.bullets %}- {{ bullet }}
{% endfor %}
{% endfor %}

## Plano de Evolucao
{% if learning_plan %}
{% for item in learning_plan %}- {{ item }}
{% endfor %}
{% else %}
- Sem gaps criticos identificados para esta vaga.
{% endif %}
"""

COVER_TEMPLATE = """# Apresentacao {{ tone }}

Ola time da {{ job.company }},

Tenho interesse na vaga **{{ job.title }}** e posso contribuir com {{ highlighted_skills }}.
{% if tone == 'curto' %}
Executo com foco em resultado, aprendizado rapido e colaboracao.
{% elif tone == 'medio' %}
Tenho historico de automacao e entrega com impacto mensuravel, mantendo qualidade tecnica.
{% else %}
Quero construir solucoes de produto com impacto real e visao de longo prazo.
{% endif %}
"""

CHECKLIST_TEMPLATE = """# Checklist de aplicacao - {{ job.company }} / {{ job.title }}

## Requisitos atendidos
{% for req in met %}- [x] {{ req }}
{% endfor %}

## Gaps e plano
{% for gap in gaps %}- [ ] {{ gap }} (em aprendizagem / experiencia em projetos)
{% endfor %}
"""

MATCH_ANALYSIS_TEMPLATE = """# Match Analysis - {{ job.company }} / {{ job.title }}

## Score detalhado (base)
- score final: {{ score_result.score }}
- skills: +{{ score_result.breakdown.skill_match_score }}
- seniority: +{{ score_result.breakdown.seniority_score }}
- location: +{{ score_result.breakdown.location_score }}
- keyword_density: +{{ score_result.breakdown.keyword_density_score }}
- red_flags: -{{ score_result.breakdown.red_flag_penalty }}

## Preference adjustments
{% for key, value in score_result.preference_adjustments.items() %}- {{ key }}: {{ value }}
{% endfor %}

## Top matched terms
{% for term in score_result.top_matched_terms %}- {{ term }}
{% endfor %}

## Gaps
{% for gap in score_result.gaps %}- {{ gap }}
{% endfor %}

## O que o sistema aprendeu de voce
{% for item in learned_signals %}- {{ item }}
{% endfor %}

## Recommendation
{{ recommendation }}
"""


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def select_relevant_bullets(profile: CandidateProfile, anchors: JobAnchors) -> list[str]:
    selected: list[str] = []
    anchor_text = " ".join(anchors.top_skills + anchors.must_have + anchors.responsibilities + anchors.mission_keywords).lower()
    mapping = {
        "mobile": ["flutter", "kotlin", "android", "ios", "mobile"],
        "backend": ["api", "backend", "python", "java", "fastapi"],
        "data": ["sql", "bi", "dashboard", "analytics", "power bi"],
        "automation": ["automacao", "automation", "rpa"],
        "leadership": ["lideranca", "leadership", "mentoria", "ownership"],
    }
    for bucket, terms in mapping.items():
        if any(term in anchor_text for term in terms):
            selected.extend(profile.bullet_bank.get(bucket, []))
    deduped: list[str] = []
    seen: set[str] = set()
    for bullet in selected:
        if bullet not in seen:
            seen.add(bullet)
            deduped.append(bullet)
    if deduped:
        return deduped[:8]
    return [f"Aprendizado ativo em {item} com aplicacao em projetos praticos." for item in (profile.learning_plan or anchors.must_have[:3])][:4]


def _rank_experiences(profile: CandidateProfile, focus_terms: list[str]) -> list[dict[str, object]]:
    ranking: list[tuple[int, dict[str, object]]] = []
    for exp in profile.experiences:
        text = " ".join(exp.bullets).lower()
        ranking.append((sum(term.lower() in text for term in focus_terms), exp.model_dump()))
    ranking.sort(key=lambda item: item[0], reverse=True)
    return [item[1] for item in ranking]


def _learned_signals(dynamic_profile_path: Path) -> list[str]:
    if not dynamic_profile_path.exists():
        return ["Sem historico suficiente ainda."]
    data = json.loads(dynamic_profile_path.read_text(encoding="utf-8"))
    top = data.get("top_skills_inferred", [])[:4]
    locations = data.get("preferred_locations", [])[:2]
    return [
        f"Skills inferidas prioritarias: {', '.join(top) if top else 'n/a'}",
        f"Locais preferidos: {', '.join(locations) if locations else 'n/a'}",
    ]


def build_artifacts(job: JobPosting, profile: CandidateProfile, artifacts_dir: Path, anchors: JobAnchors, score_result: ScoringResult, dynamic_profile_path: Path) -> ArtifactBundle:
    reqs = job.requirements or [job.description]
    focus_skills = anchors.top_skills[:5] or profile.stacks[:5]
    selected_bullets = select_relevant_bullets(profile, anchors)
    file_token = safe_filename_token(job.external_id)

    ranked_exps = _rank_experiences(profile, focus_skills)
    if ranked_exps:
        ranked_exps[0]["bullets"] = selected_bullets

    summary_lines = [
        f"Profissional focado em {', '.join(focus_skills[:3])} para contexto de {job.title}.",
        "Entrego iniciativas com impacto mensuravel em eficiencia, qualidade e tempo de resposta.",
        "Atuo com clareza tecnica e visao de produto, sem extrapolar experiencia real.",
    ]
    met = [req for req in reqs if any(skill.lower() in req.lower() for skill in focus_skills)]
    gaps = [req for req in reqs if req not in met]
    learning_plan = profile.learning_plan if gaps else []

    resume_path = artifacts_dir / f"resume_{file_token}.md"
    _write(resume_path, Template(RESUME_TEMPLATE).render(profile=profile, focus_skills=focus_skills, ranked_experiences=ranked_exps, learning_plan=learning_plan, summary_lines=summary_lines))

    cover_paths: list[str] = []
    for tone in ["curto", "medio", "visionario"]:
        cover_path = artifacts_dir / f"cover_{tone}_{file_token}.md"
        _write(cover_path, Template(COVER_TEMPLATE).render(job=job, tone=tone, highlighted_skills=", ".join(focus_skills[:4])))
        cover_paths.append(str(cover_path))

    dm_path = artifacts_dir / f"outreach_dm_{file_token}.txt"
    _write(dm_path, f"Oi! Vi a vaga {job.title} na {job.company}. Tenho aderencia em {', '.join(focus_skills[:3])} e posso enviar CV adaptado.")

    email_path = artifacts_dir / f"outreach_email_{file_token}.txt"
    _write(email_path, f"Assunto: Candidatura - {job.title}\n\nPrezados, tenho interesse na vaga e experiencia pratica com {', '.join(focus_skills[:4])}.\nPosso contribuir com execucao consistente e evolucao continua.\n\nAtenciosamente.")

    checklist_path = artifacts_dir / f"application_checklist_{file_token}.md"
    _write(checklist_path, Template(CHECKLIST_TEMPLATE).render(job=job, met=met, gaps=gaps))

    match_analysis_path = artifacts_dir / f"match_analysis_{file_token}.md"
    _write(match_analysis_path, Template(MATCH_ANALYSIS_TEMPLATE).render(job=job, score_result=score_result, learned_signals=_learned_signals(dynamic_profile_path), recommendation=recommendation_from_score(score_result.score)))

    project_prompt_path = write_project_prompt(artifacts_dir, job, anchors, profile)

    return ArtifactBundle(resume_path=str(resume_path), cover_paths=cover_paths, dm_path=str(dm_path), email_path=str(email_path), checklist_path=str(checklist_path), match_analysis_path=str(match_analysis_path), project_prompt_path=str(project_prompt_path))
