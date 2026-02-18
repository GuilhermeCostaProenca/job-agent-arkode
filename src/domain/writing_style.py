from __future__ import annotations

import re
from collections import Counter


def compute_writing_delta(original_text: str, final_text: str) -> dict[str, float | int]:
    orig_tokens = re.findall(r"\w+", original_text.lower())
    final_tokens = re.findall(r"\w+", final_text.lower())
    orig_set = set(orig_tokens)
    final_set = set(final_tokens)

    added = final_set - orig_set
    removed = orig_set - final_set

    contractions = {"vc", "pra", "tb", "né", "q"}
    confidence_words = {"certamente", "posso", "tenho", "conseguirei", "entrego"}

    delta = {
        "length_ratio": round(len(final_text) / max(1, len(original_text)), 3),
        "punctuation_delta": final_text.count("!")
        + final_text.count("?")
        - original_text.count("!")
        - original_text.count("?"),
        "eu_vs_nos": final_text.lower().count(" eu ") - final_text.lower().count(" nós "),
        "formality_score": float(
            sum(1 for token in final_tokens if token in contractions) * -1
            + final_text.count("Prezados")
            + final_text.count("Atenciosamente")
        ),
        "confidence_score": float(sum(1 for token in final_tokens if token in confidence_words)),
        "added_terms": int(len(added)),
        "removed_terms": int(len(removed)),
    }

    freq = Counter(final_tokens)
    delta["directness_score"] = float(
        freq.get("objetivo", 0) + freq.get("direto", 0) - freq.get("talvez", 0)
    )
    return delta
