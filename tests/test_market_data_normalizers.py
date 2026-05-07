from __future__ import annotations

import math

import pandas as pd
import pytest

from market_data.normalizers import (
    calculate_historical_fundamental,
    normalize_history_points,
    normalize_metric_value,
    normalize_symbol,
    price_history_points,
    to_float,
)


def test_normalize_symbol_trims_and_uppercases():
    assert normalize_symbol(" aapl ") == "AAPL"


@pytest.mark.parametrize("value", [None, "", "not-a-number", math.inf, -math.inf, math.nan])
def test_to_float_rejects_missing_invalid_and_non_finite_values(value):
    assert to_float(value) is None


def test_to_float_accepts_numeric_strings_and_numbers():
    assert to_float("18.5") == 18.5
    assert to_float(18) == 18.0


def test_normalize_metric_value_uses_metric_definition_multiplier():
    assert normalize_metric_value("roe", 0.1234) == 12.34
    assert normalize_metric_value("profitmargins", 0.25) == 25.0
    assert normalize_metric_value("dividendyield", 0.021) == 2.1
    assert normalize_metric_value("payoutratio", 0.35) == 35.0
    assert normalize_metric_value("pe", 18.5) == 18.5


def test_normalize_history_points_skips_invalid_values_and_normalizes_percentages():
    series = pd.Series(
        [0.1, None, 0.2],
        index=pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-03"]),
    )

    assert normalize_history_points(series, "roe") == [
        {"date": "2026-01-01", "value": 10.0},
        {"date": "2026-01-03", "value": 20.0},
    ]


def test_price_history_points_uses_close_column_and_skips_invalid_values():
    history = pd.DataFrame(
        {"Close": [100.0, None, 102.5]},
        index=pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-03"]),
    )

    assert price_history_points(history) == [
        {"date": "2026-01-01", "value": 100.0},
        {"date": "2026-01-03", "value": 102.5},
    ]


def test_price_history_points_returns_empty_without_close_column():
    history = pd.DataFrame(
        {"Open": [100.0]},
        index=pd.to_datetime(["2026-01-01"]),
    )

    assert price_history_points(history) == []


def test_calculate_historical_fundamental_forward_fills_roe_to_history_index():
    statement_date = pd.Timestamp("2026-03-31")
    income_statement = pd.DataFrame(
        {statement_date: [25.0]},
        index=["Net Income"],
    )
    balance_sheet = pd.DataFrame(
        {statement_date: [100.0]},
        index=["Stockholders Equity"],
    )
    history_index = pd.to_datetime(["2026-03-31", "2026-04-01"])

    series = calculate_historical_fundamental(
        income_statement,
        balance_sheet,
        "roe",
        history_index,
    )

    assert series.tolist() == [0.25, 0.25]
