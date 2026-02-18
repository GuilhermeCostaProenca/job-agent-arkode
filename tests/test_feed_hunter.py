from src.domain.hiring_signals import detect_hiring_signal


def test_detect_hiring_signal() -> None:
    result = detect_hiring_signal("We're hiring mobile engineers. Join our team!")
    assert result.is_hiring
    assert result.confidence > 0
    assert result.triggers
