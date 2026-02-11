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
4. **Rodar pipeline diário**
   ```bash
   jobagent run --sources rss,manual --limit 30 --manual-url https://example.com/jobs/mobile-junior
   ```
5. **Inspecionar resultados**
   ```bash
   jobagent list --top 20 --min-score 60
   jobagent artifacts <job_id>
   ```

## Learning loop (v0.3.0)
- Eventos do usuário são gravados em `user_signals` (aprovação, rejeição, applied, replied, interview, offer, artifact_edit).
- `preference_model` é atualizado incrementalmente com base nesses sinais.
- O score final combina breakdown base + ajustes de preferência.
- `profile_dynamic.json` é atualizado no fim do pipeline com sinais aprendidos.

## Como reverter aprendizado
```bash
jobagent preferences show
jobagent preferences reset
```

## Comandos CLI novos
- `jobagent reject <job_id> --reason "..."`
- `jobagent applied <job_id>`
- `jobagent replied <job_id> --channel email|linkedin|whatsapp`
- `jobagent interview <job_id> --date YYYY-MM-DD --notes "..."`
- `jobagent offer <job_id> --notes "..."`
- `jobagent signal list --last 50`
- `jobagent artifact-edit <job_id> --name cover --file path/to/final.txt`
- `jobagent preferences show`
- `jobagent preferences reset`

## API (FastAPI)
```bash
uvicorn src.api.main:app --reload
```

Novos endpoints:
- `POST /signals`
- `GET /signals?limit=50`
- `POST /applications/{job_id}/status`
- `POST /artifacts/{job_id}/edited`

## Segurança e conformidade
- Sem bypass de captcha/2FA/login.
- Sem disparo em massa de outreach.
- Sem inventar experiência/skill.
- Aprovação humana obrigatória para envio final.
