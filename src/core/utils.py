from collections.abc import Iterable


def normalize_text(value: str) -> str:
    return " ".join(value.strip().lower().split())


def keyword_overlap(target_keywords: set[str], text_tokens: Iterable[str]) -> float:
    tokens = {token.lower() for token in text_tokens}
    if not target_keywords:
        return 0.0
    return len(target_keywords.intersection(tokens)) / len(target_keywords)
