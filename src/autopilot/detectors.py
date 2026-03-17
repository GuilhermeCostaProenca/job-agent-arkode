CAPTCHA_HINTS = ("captcha", "i am human", "recaptcha")
TWO_FACTOR_HINTS = ("2fa", "two-factor", "otp", "verification code", "authenticator")
SESSION_HINTS = ("session expired", "session invalid", "sign in again", "login required", "sessao expirada")
LOGIN_HINTS = ("login", "sign in")


def detect_captcha_or_auth(html_content: str) -> str | None:
    text = html_content.lower()
    if "no captcha" in text or "without captcha" in text:
        return None
    if any(hint in text for hint in CAPTCHA_HINTS):
        return "captcha_detected"
    if any(hint in text for hint in TWO_FACTOR_HINTS):
        return "two_factor_required"
    if any(hint in text for hint in SESSION_HINTS):
        return "session_invalid"
    if any(hint in text for hint in LOGIN_HINTS):
        return "auth_required"
    return None
