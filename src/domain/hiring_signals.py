from __future__ import annotations

from dataclasses import dataclass

TRIGGERS = [
    "we're hiring",
    "hiring",
    "vaga",
    "contratando",
    "indicação",
    "join our team",
    "opportunity",
]


@dataclass
class HiringSignalResult:
    is_hiring: bool
    confidence: float
    triggers: list[str]
    suggested_action: str


def detect_hiring_signal(text: str) -> HiringSignalResult:
    lower = text.lower()
    hits = [trigger for trigger in TRIGGERS if trigger in lower]
    confidence = min(0.99, len(hits) * 0.22)
    is_hiring = bool(hits)
    action = "generate_outreach_drafts" if is_hiring else "ignore"
    return HiringSignalResult(
        is_hiring=is_hiring,
        confidence=confidence,
        triggers=hits,
        suggested_action=action,
    )
