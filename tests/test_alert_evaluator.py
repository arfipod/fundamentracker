import pytest

from alert_evaluator import calculate_relative_diff, evaluate_alert


def test_evaluate_absolute_alerts():
    assert evaluate_alert(18, 20, "<", "absolute") is True
    assert evaluate_alert(22, 20, "<", "absolute") is False
    assert evaluate_alert(20, 20, ">=", "absolute") is True


def test_evaluate_relative_alert_positive_target():
    assert calculate_relative_diff(110, 100) == pytest.approx(10)
    assert evaluate_alert(110, 5, ">", "relative", 100) is True
    assert evaluate_alert(103, 5, ">", "relative", 100) is False


def test_evaluate_relative_alert_negative_target():
    assert calculate_relative_diff(90, 100) == pytest.approx(-10)
    assert evaluate_alert(90, -5, "<", "relative", 100) is True
    assert evaluate_alert(97, -5, "<", "relative", 100) is False


def test_relative_alert_without_reference_is_not_evaluated_as_absolute():
    assert evaluate_alert(10, 20, "<", "relative", None) is False
    assert evaluate_alert(10, 20, "<", "relative", 0) is False
