from src.domain.reasons import APPROVED_REASONS, REJECTED_REASONS, is_valid_reason


def test_reason_taxonomy_validation() -> None:
    assert "like_company" in APPROVED_REASONS
    assert "salary_low" in REJECTED_REASONS
    assert is_valid_reason("good_learning")
    assert not is_valid_reason("unknown_reason")
