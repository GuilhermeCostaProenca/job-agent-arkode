import re
from collections.abc import Iterable


def normalize_text(text: str) -> str:
    return " ".join(token.strip().lower() for token in text.split() if token.strip())


def tokenize_text(text: str) -> list[str]:
    return [token for token in normalize_text(text).split(" ") if token]


def keyword_overlap(target_keywords: set[str], text_tokens: Iterable[str]) -> float:
    tokens = {token.strip().lower() for token in text_tokens if token.strip()}
    if not target_keywords:
        return 0.0
    return len(target_keywords.intersection(tokens)) / len(target_keywords)


def safe_filename_token(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    token = cleaned.strip("._")
    return token or "job"
