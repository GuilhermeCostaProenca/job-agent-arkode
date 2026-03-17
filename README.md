# job-agent-arkode

Agente pessoal de IA para descobrir vagas, gerar materiais sob medida, acompanhar candidaturas e operar um cockpit web.

## Stack
- Backend: FastAPI + SQLModel
- Automacao: Playwright connectors
- Frontend: Next.js
- Persistencia: SQLite por padrao, pronto para PostgreSQL

## Desenvolvimento
```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m uvicorn src.api.main:app --reload --port 8000
```

Frontend:
```powershell
cd apps/web
pnpm install
pnpm dev
```

## Endpoints principais
- `GET /dashboard`
- `GET/PUT /profile`
- `GET /jobs`
- `POST /applications/apply`
- `GET /applications`
- `POST /email/sync`
- `GET /mcp/tools`
