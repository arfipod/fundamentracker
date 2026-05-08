from __future__ import annotations

import math
from typing import Any

import pandas as pd

from market_data.metric_definitions import get_metric_definition


def normalize_symbol(symbol: str) -> str:
    return symbol.strip().upper()


def to_float(value: Any) -> float | None:
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None

    if not math.isfinite(numeric):
        return None
    return numeric


def normalize_metric_value(metric: str, value: Any) -> float | None:
    numeric = to_float(value)
    if numeric is None:
        return None

    definition = get_metric_definition(metric)
    return numeric * definition.multiplier


def normalize_history_points(series: pd.Series, metric: str) -> list[dict[str, float | str]]:
    data: list[dict[str, float | str]] = []
    for date, value in series.items():
        normalized = normalize_metric_value(metric, value)
        if normalized is None:
            continue
        data.append({"date": pd.Timestamp(date).strftime("%Y-%m-%d"), "value": normalized})
    return data


def price_history_points(history: pd.DataFrame) -> list[dict[str, float | str]]:
    if history.empty or "Close" not in history:
        return []

    data: list[dict[str, float | str]] = []
    for date, row in history.iterrows():
        close = to_float(row.get("Close"))
        if close is None:
            continue
        data.append({"date": pd.Timestamp(date).strftime("%Y-%m-%d"), "value": close})
    return data


def calculate_historical_fundamental(
    income_statement: pd.DataFrame,
    balance_sheet: pd.DataFrame,
    metric_name: str,
    history_index: pd.Index,
) -> pd.Series:
    metric_name = metric_name.lower()
    q_inc = income_statement.T if income_statement is not None and not income_statement.empty else pd.DataFrame()
    q_bal = balance_sheet.T if balance_sheet is not None and not balance_sheet.empty else pd.DataFrame()
    q_df = pd.concat([q_inc, q_bal], axis=1).sort_index()

    if q_df.empty:
        return pd.Series(index=history_index, dtype=float)

    values = []
    dates = []

    for date, row in q_df.iterrows():
        val = None

        if metric_name == "roe":
            net_income = row.get("Net Income", 0)
            equity = row.get("Stockholders Equity", 0)
            if pd.notna(net_income) and pd.notna(equity) and equity != 0:
                val = net_income / equity

        elif metric_name == "roic":
            ebit = row.get("EBIT", 0)
            if pd.isna(ebit):
                pretax_income = row.get("Pretax Income", 0)
                interest_expense = row.get("Interest Expense", 0)
                ebit = (pretax_income if pd.notna(pretax_income) else 0) + (
                    interest_expense if pd.notna(interest_expense) else 0
                )

            tax_provision = row.get("Tax Provision", 0)
            pretax_income = row.get("Pretax Income", 0)
            tax_rate = (
                tax_provision / pretax_income
                if pd.notna(tax_provision) and pd.notna(pretax_income) and pretax_income != 0
                else 0.21
            )
            nopat = ebit * (1 - tax_rate)

            debt = row.get("Total Debt", 0)
            equity = row.get("Stockholders Equity", 0)
            if pd.isna(debt):
                debt = 0
            if pd.isna(equity):
                equity = 0

            if (debt + equity) != 0:
                val = nopat / (debt + equity)

        elif metric_name == "debttoequity":
            debt = row.get("Total Debt", 0)
            equity = row.get("Stockholders Equity", 0)
            if pd.notna(debt) and pd.notna(equity) and equity != 0:
                val = debt / equity

        elif metric_name == "profitmargins":
            net_income = row.get("Net Income", 0)
            total_revenue = row.get("Total Revenue", 0)
            if pd.notna(net_income) and pd.notna(total_revenue) and total_revenue != 0:
                val = net_income / total_revenue

        elif metric_name == "operatingmargins":
            operating_income = row.get("Operating Income", 0)
            total_revenue = row.get("Total Revenue", 0)
            if pd.notna(operating_income) and pd.notna(total_revenue) and total_revenue != 0:
                val = operating_income / total_revenue

        if val is not None:
            values.append(val)
            dates.append(date)

    if not values:
        return pd.Series(index=history_index, dtype=float)

    series = pd.Series(values, index=dates).sort_index()
    series.index = pd.to_datetime(series.index)
    history_tz = getattr(history_index, "tz", None)
    if history_tz is not None and series.index.tz is None:
        series.index = series.index.tz_localize(history_tz)

    combined = pd.concat([pd.Series(index=history_index, dtype=float), series], axis=1)
    combined = combined.iloc[:, 1].ffill()
    return combined.loc[history_index]
