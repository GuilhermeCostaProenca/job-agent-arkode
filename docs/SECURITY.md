# Segurança

- Nunca comitar credenciais reais (`.env` no `.gitignore`).
- Armazenar tokens e SMTP apenas por variáveis de ambiente.
- Autopilot explicitamente não contorna captcha, anti-bot, 2FA ou login protegido.
- Envios de outreach são rascunhos no MVP com aprovação humana obrigatória.
- Logs são estruturados com `run_id` para auditoria.
