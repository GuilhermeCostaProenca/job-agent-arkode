# Architecture

## Backend
- FastAPI expoe rotas para perfil, jobs, applications, dashboard, email e catalogo MCP.
- `TrackerRepository` concentra persistencia operacional.
- `services/` implementa perfil, candidatura, inbox e tools catalog.

## Automation
- `src/autopilot/connectors.py` resolve conectores por URL.
- Toda execucao gera `ExecutionRun` + `ExecutionEvent`.
- Browser sessions e credential states ficam persistidos para retomada segura.

## Frontend
- Next.js opera como cockpit com dashboard, profile, applications, inbox e jobs.
