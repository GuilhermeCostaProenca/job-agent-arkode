from src.domain.writing_style import compute_writing_delta


def test_writing_delta_has_expected_keys() -> None:
    original = "Olá, tenho interesse na vaga."
    final = "Prezados, tenho experiência e certamente posso contribuir objetivamente."
    delta = compute_writing_delta(original, final)
    keys = {
        "length_ratio",
        "punctuation_delta",
        "eu_vs_nos",
        "formality_score",
        "confidence_score",
        "added_terms",
        "removed_terms",
        "directness_score",
    }
    assert keys.issubset(delta.keys())
