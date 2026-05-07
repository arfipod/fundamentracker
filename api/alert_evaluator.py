from __future__ import annotations

from config import OPERATORS_MAP


def calculate_relative_diff(
    current_value: float | int | None,
    reference_value: float | int | None,
) -> float | None:
    if current_value is None or reference_value is None:
        return None

    reference = float(reference_value)
    if reference == 0:
        return None

    return ((float(current_value) / reference) - 1) * 100


def evaluate_alert(
    current_value: float | int | None,
    target: float | int,
    operator: str,
    alert_type: str | None = "absolute",
    reference_value: float | int | None = None,
) -> bool:
    op_func = OPERATORS_MAP.get(operator)
    if op_func is None or current_value is None:
        return False

    comparison_value = current_value
    if alert_type == "relative":
        diff = calculate_relative_diff(current_value, reference_value)
        if diff is None:
            return False
        comparison_value = diff

    return bool(op_func(float(comparison_value), float(target)))
