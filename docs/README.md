# job-agent-arkode

Agente diário de vagas (Python-first) com human-in-the-loop para descoberta, priorização, personalização de candidatura e autopilot seguro até o ponto de envio.

## Quickstart (5 minutos)
1. **Criar ambiente e instalar deps**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -e .[dev]
   ```
2. **Configurar env**
   ```bash
   cp .env.example .env
   ```
3. **Revisar perfil**
   ```bash
   nano data/profile.yaml
   ```
4. **Rodar pipeline diário (MVP)**
   ```bash
   jobagent run --sources rss,manual --limit 30 --manual-url https://example.com/jobs/mobile-junior
   ```
5. **Inspecionar resultados**
   ```bash
   jobagent list --top 20 --min-score 60
   jobagent artifacts <job_id>
   ```

## How tailoring v2 works
- Extraímos **job anchors** (skills, responsabilidades, must-have/nice-to-have, missão).
- Selecionamos bullets do `bullet_bank` do perfil de forma contextual.
- Reordenamos experiências por relevância.
- Geramos novos artifacts: `match_analysis_<job_id>.md` e `project_prompt_<job_id>.md`.
- Quando houver gap, adicionamos seção **Plano de Evolução** sem inventar experiência.

## How score breakdown works
O score é composto por:
- `skill_match_score`
- `seniority_score`
- `location_score`
- `keyword_density_score`
- `red_flag_penalty`

A CLI mostra o breakdown:
```text
score: 84
[skills +30 | seniority +20 | location +15 | keywords +19 | red_flags -0]
```

## How to use project launcher
Depois de um `jobagent run`, cada vaga ganha um artifact:
- `artifacts/project_prompt_<job_id>.md`

Esse arquivo traz mini-projeto estratégico com:
- problema
- stack sugerida
- user stories
- estrutura de pastas
- prompt pronto para Codex

## Comandos CLI
- `jobagent run --sources rss,manual --limit 30`
- `jobagent list --top 20`
- `jobagent artifacts <job_id>`
- `jobagent approve <approval_id> --yes/--no`
- `jobagent export --format csv --min-score 70`
- `jobagent followups`

## API (FastAPI)
```bash
uvicorn src.api.main:app --reload
```

Endpoints principais:
- `GET /jobs?status=new&min_score=70`
- `GET /jobs/{id}`
- `GET /runs`
- `POST /approvals/{id}/approve`
- `POST /approvals/{id}/reject`

## Regras de segurança e conformidade
- Sem bypass de captcha/2FA/login.
- Sem disparo em massa de outreach.
- Sem inventar experiência/skill.
- Aprovação humana obrigatória para envio final.

## Demo e2e com fixtures
Use `fixtures/mock_jobs.json` para simular vagas e validar scoring/tailoring localmente via testes.
