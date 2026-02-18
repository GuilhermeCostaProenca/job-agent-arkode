CAPTCHA_HINTS = ("captcha", "i am human", "recaptcha")
LOGIN_HINTS = ("2fa", "two-factor", "otp", "login")


def detect_captcha_or_auth(html_content: str) -> str | None:
    text = html_content.lower()
    if any(hint in text for hint in CAPTCHA_HINTS):
        return "captcha_detected"
    if any(hint in text for hint in LOGIN_HINTS):
        return "auth_required"
    return None
