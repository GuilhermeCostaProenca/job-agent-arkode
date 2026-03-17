from __future__ import annotations


PAUSE_ACTIONS = {
    "manual_review_before_submit": "Revisar os artefatos e confirmar a submissao final.",
    "captcha_detected": "Abrir a plataforma no navegador persistente e resolver o captcha manualmente.",
    "two_factor_required": "Concluir a verificacao 2FA e retomar a execucao.",
    "session_invalid": "Refazer o login da plataforma e validar a sessao antes de retomar.",
    "auth_required": "Validar credenciais da plataforma e autenticar novamente.",
    "session_setup_required": "Abrir a sessao persistente da plataforma e concluir o login manualmente.",
    "low_confidence_answer": "Revisar a resposta sugerida e aprovar ou editar antes de continuar.",
    "browser_dependency_missing": "Instalar Playwright e o browser Chromium antes de usar o conector real.",
    "linkedin_easy_apply_unavailable": "Abrir a vaga no LinkedIn e validar se o botao Easy Apply esta disponivel.",
    "linkedin_form_requires_review": "Revisar manualmente o formulario do LinkedIn porque ha campos obrigatorios ainda nao suportados.",
}


def build_pause_context(reason: str, detail: str = "") -> dict[str, str]:
    recommendation = PAUSE_ACTIONS.get(reason, "Revisar a execucao pausada no painel antes de continuar.")
    return {
        "pause_reason": reason,
        "recommended_action": recommendation,
        "detail": detail,
    }
