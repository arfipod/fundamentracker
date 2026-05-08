import pytest

from alert_evaluator import calculate_relative_diff, evaluate_alert


def test_absolute_alert_evaluation_uses_configured_operator():
    assert evaluate_alert(18, 20, "<", "absolute") is True
    assert evaluate_alert(22, 20, "<", "absolute") is False
    assert evaluate_alert(20, 20, ">=", "absolute") is True
    assert evaluate_alert(20, 20, "=", "absolute") is True


def test_relative_alert_evaluation_compares_percent_diff_to_target():
    assert calculate_relative_diff(110, 100) == pytest.approx(10)
    assert evaluate_alert(110, 5, ">", "relative", 100) is True
    assert evaluate_alert(103, 5, ">", "relative", 100) is False


def test_relative_alert_evaluation_handles_negative_moves():
    assert calculate_relative_diff(90, 100) == pytest.approx(-10)
    assert evaluate_alert(90, -5, "<", "relative", 100) is True
    assert evaluate_alert(97, -5, "<", "relative", 100) is False


def test_relative_alert_without_reference_is_not_evaluated_as_absolute():
    assert evaluate_alert(10, 20, "<", "relative", None) is False
    assert evaluate_alert(10, 20, "<", "relative", 0) is False


def test_duplicate_same_metric_alert_rules_are_independent():
    current_pe = 45
    low_alert = evaluate_alert(current_pe, 20, "<", "absolute")
    high_alert = evaluate_alert(current_pe, 40, ">", "absolute")

    assert low_alert is False
    assert high_alert is True


def test_invalid_inputs_do_not_trigger_alerts():
    assert calculate_relative_diff(None, 100) is None
    assert calculate_relative_diff(100, None) is None
    assert evaluate_alert(None, 20, "<", "absolute") is False
    assert evaluate_alert(18, 20, "invalid", "absolute") is False
