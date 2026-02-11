# Arquitetura v0.3.0

## Fluxo diário
1. Ingestão + normalização + dedupe.
2. Extração de anchors da vaga.
3. Scoring base explicável.
4. Ajustes de preferência via learning loop.
5. Tailoring v2 + artifacts estratégicos.
6. Persistência de jobs/applications/signals/writing deltas.
7. Atualização de `profile_dynamic.json`.

## Learning loop
- `user_signals`: ledger de eventos do usuário.
- `preference_model`: pesos adaptativos por skill/local/senioridade/estilo.
- `writing_deltas`: captura de edição de artifacts para aprender estilo.
- Processamento incremental via `last_processed_signal_id`.

## Multi-user ready
Ainda single-user por padrão, porém tabelas principais incluem `user_id` com default `default`.
Próximo passo para multi-tenant: auth + scoping de `user_id` por token/sessão.

## Como resetar preferências
CLI `jobagent preferences reset` reescreve `preference_model` para pesos padrão.
