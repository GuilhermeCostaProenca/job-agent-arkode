# apps/web

Frontend web do `job-agent-arkode` com Next.js (App Router) + TypeScript + Tailwind.

## Requisitos
- Node 20+
- pnpm
- API FastAPI rodando (default `http://localhost:8000`)

## Rodando API + Web
No backend (raiz do repo):
```bash
uvicorn src.api.main:app --reload --port 8000
```

No frontend:
```bash
cd apps/web
cp .env.example .env.local
pnpm install
pnpm dev
```

Abrir: `http://localhost:3000`

## Env
- `NEXT_PUBLIC_API_BASE=http://localhost:8000`
