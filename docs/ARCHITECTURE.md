# Arquitetura MVP -> v0.2.0

O projeto segue arquitetura modular Python-first com `src/` separando domínio, ingestão, tracker, API, CLI e autopilot.

## Fluxo diário
1. Scheduler/API ou CLI dispara run diário.
2. Coleta de vagas por RSS + manual URL.
3. Normalização + deduplicação + extração de anchors.
4. Scoring explicável com breakdown + recomendação.
5. Tailoring v2 (bullet bank, plano de evolução, match analysis).
6. Geração de prompt de mini-projeto estratégico (CodexLauncher).
7. Persistência no tracker SQLite (`jobs`, `runs`, `artifacts`, `approvals`, `applications`).

## How tailoring v2 works
- Anchors capturam sinais da vaga por seção (`Requisitos`, `Responsabilidades`, `Diferenciais`, `About`).
- Seleção de bullets é orientada por mapa de termos (mobile/backend/data/automation/leadership).
- Se faltarem bullets aderentes, usamos `learning_plan` do perfil.

## How score breakdown works
Cada vaga armazena `score_breakdown_json` com os componentes numéricos para auditoria e exibição em CLI/API.

## How to use project launcher
Para cada vaga processada é criado `project_prompt_<job_id>.md` com prompt pronto para construir projeto-prova alinhado às top skills.

## Next steps
- Migrações Alembic e Postgres nativo.
- Busca semântica para anchors e ranking.
- UI de revisão para aprovação e follow-ups.
