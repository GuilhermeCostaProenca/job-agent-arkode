# job-agent-arkode

Agente diário de vagas com human-in-the-loop e aprendizado incremental.

## v0.4.0 highlights
- Taxonomia de motivos para approve/reject.
- Estratégia de exploração 80/20 para evitar bolha.
- Aprendizado ponderado por outcome (`replied/interview/offer`).
- Feed Hunter para detectar hiring signals e gerar drafts de outreach.

## Reason taxonomy
Approved:
- like_company, like_role, good_growth, good_learning, good_stack_match

Rejected:
- stack_mismatch, seniority_too_high, salary_low, location_bad,
  company_type_bad, description_generic, red_flag_pj, red_flag_unpaid,
  support_disguised, commute_too_far

## Exploration strategy (80/20)
- 80% vagas de maior score.
- 20% exploração com novidade (skill nova, empresa nova ou localização nova).
- CLI: `jobagent list --explore`

## Outcome-weighted learning
Pesos por sinal:
- offer +5x
- interview +3x
- replied +2x
- applied +1.5x
- approval +1x
- rejected -1x

## Feed Hunter
- `jobagent feed add --url <...>`
- `jobagent feed add --file feed.json`
- `jobagent feed list --hiring-only`
- API: `GET /feed?hiring_only=true`
- API: `POST /feed/{id}/drafts`

## Segurança
- Sem bypass de captcha/login/2FA.
- Sem envio automático sem aprovação humana.
- Sem inventar experiências/skills.
