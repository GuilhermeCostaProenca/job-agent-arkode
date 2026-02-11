# Arquitetura MVP

O projeto segue arquitetura modular Python-first com `src/` separando domínio, ingestão, tracker, API, CLI e autopilot.

## Fluxo diário
1. Scheduler/API ou CLI dispara run diário.
2. Coleta de vagas por RSS + manual URL.
3. Normalização + deduplicação + score (0-100 com explicação).
4. Geração de artifacts (CV adaptado, covers, outreach, checklist).
5. Persistência no tracker SQLite (`jobs`, `runs`, `artifacts`, `approvals`).
6. Autopilot (feature flag) executa preenchimento até submit e cria aprovação humana.

## Next steps
- Trocar heurística por modelo de ranking híbrido.
- Suporte a Postgres e Alembic.
- Painel web com aprovação inline e histórico de versões de artifacts.
