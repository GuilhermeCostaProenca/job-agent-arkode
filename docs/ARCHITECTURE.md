# Arquitetura v0.4.0

## Core loop
1. Ingest + normalize + dedupe.
2. Anchors e scoring explicável.
3. Ajustes por preference engine com aprendizado incremental.
4. Recomendação com exploração controlada 80/20.
5. Tailoring + artifacts + revisão humana.

## Signals & reasons
- `user_signals` guarda evento + payload_json (reason/notes/etc).
- Taxonomia controlada melhora consistência de aprendizado.

## Outcome-weighted learning
- Modelo de preferências usa multiplicadores por resultado.
- Sinais mais fortes (`offer/interview`) aceleram ajuste dos pesos.

## Feed Hunter
- `feed_items` armazena entradas manuais (URL/texto).
- Detector de hiring signals classifica confiança e triggers.
- Geração de drafts multi-canal em artifacts; envio continua humano.

## Multi-user ready
- tabelas principais possuem `user_id` default `default`.
