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

## Comandos CLI
- `jobagent run --sources rss,manual --limit 30`
- `jobagent list --top 20`
- `jobagent artifacts <job_id>`
- `jobagent approve <approval_id> --yes/--no`

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
