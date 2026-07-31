from __future__ import annotations

import math
import re
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


def _normalized_label(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def _statement_table(statement: pd.DataFrame | None) -> pd.DataFrame:
    if statement is None or statement.empty:
        return pd.DataFrame()
    table = statement.T.copy()
    table.index = pd.to_datetime(table.index, errors="coerce")
    table = table[~table.index.isna()].sort_index()
    return table.apply(pd.to_numeric, errors="coerce")


def _matching_column(table: pd.DataFrame, *aliases: str) -> str | None:
    aliases_normalized = {_normalized_label(alias) for alias in aliases}
    return next(
        (column for column in table.columns if _normalized_label(column) in aliases_normalized),
        None,
    )


def _flow_sum(table: pd.DataFrame, as_of: pd.Timestamp, *aliases: str) -> float | None:
    column = _matching_column(table, *aliases)
    if column is None:
        return None
    window = pd.to_numeric(table.loc[table.index <= as_of, column], errors="coerce").dropna().tail(4)
    if window.empty:
        return None
    return to_float(window.sum())


def _balance_values(table: pd.DataFrame, as_of: pd.Timestamp, *aliases: str) -> pd.Series:
    column = _matching_column(table, *aliases)
    if column is None:
        return pd.Series(dtype=float)
    return pd.to_numeric(table.loc[table.index <= as_of, column], errors="coerce").dropna()


def _latest_balance(table: pd.DataFrame, as_of: pd.Timestamp, *aliases: str) -> float | None:
    values = _balance_values(table, as_of, *aliases)
    return to_float(values.iloc[-1]) if not values.empty else None


def _average_balance(table: pd.DataFrame, as_of: pd.Timestamp, *aliases: str) -> float | None:
    values = _balance_values(table, as_of, *aliases)
    if values.empty:
        return None
    current = to_float(values.iloc[-1])
    previous_year = to_float(values.iloc[-5]) if len(values) >= 5 else None
    if current is None:
        return None
    return (current + previous_year) / 2.0 if previous_year is not None else current


def _invested_capital_at(table: pd.DataFrame, as_of: pd.Timestamp) -> float | None:
    direct = _latest_balance(table, as_of, "Invested Capital")
    if direct is not None and direct > 0:
        return direct
    debt = _latest_balance(table, as_of, "Total Debt") or 0.0
    equity = _latest_balance(table, as_of, "Stockholders Equity", "Common Stock Equity") or 0.0
    cash = _latest_balance(
        table,
        as_of,
        "Cash Cash Equivalents And Short Term Investments",
        "Cash And Cash Equivalents",
    ) or 0.0
    value = debt + equity - cash
    return value if value > 0 else None


def _average_invested_capital(table: pd.DataFrame, as_of: pd.Timestamp) -> float | None:
    dates = table.index[table.index <= as_of]
    if len(dates) == 0:
        return None
    current = _invested_capital_at(table, dates[-1])
    previous = _invested_capital_at(table, dates[-5]) if len(dates) >= 5 else None
    if current is None:
        return None
    return (current + previous) / 2.0 if previous is not None else current


def _effective_tax_rate(income: pd.DataFrame, as_of: pd.Timestamp) -> float:
    direct_column = _matching_column(income, "Tax Rate For Calcs")
    if direct_column is not None:
        direct_values = pd.to_numeric(
            income.loc[income.index <= as_of, direct_column],
            errors="coerce",
        ).dropna()
        latest_rate = to_float(direct_values.iloc[-1]) if not direct_values.empty else None
        if latest_rate is not None and 0 <= latest_rate <= 0.5:
            return latest_rate

    tax = _flow_sum(income, as_of, "Tax Provision")
    pretax = _flow_sum(income, as_of, "Pretax Income")
    if tax is not None and pretax not in (None, 0):
        rate = tax / pretax
        if 0 <= rate <= 0.5:
            return rate
    return 0.21


def calculate_historical_fundamental(
    income_statement: pd.DataFrame,
    balance_sheet: pd.DataFrame,
    metric_name: str,
    history_index: pd.Index,
) -> pd.Series:
    """Build point-in-time fundamental history from quarterly statements.

    Flow metrics use a rolling four-quarter sum when four observations are
    available. ROE and ROIC divide those TTM flows by average beginning/ending
    capital (five quarterly balance observations); shorter histories gracefully
    use the available flow window and ending capital rather than inventing data.
    """

    metric_name = metric_name.lower()
    income = _statement_table(income_statement)
    balance = _statement_table(balance_sheet)
    statement_dates = sorted(set(income.index) | set(balance.index))
    if not statement_dates:
        return pd.Series(index=history_index, dtype=float)

    values: list[float] = []
    dates: list[pd.Timestamp] = []

    for statement_date in statement_dates:
        value: float | None = None
        net_income = _flow_sum(income, statement_date, "Net Income", "Net Income Common Stockholders")
        revenue = _flow_sum(income, statement_date, "Total Revenue", "Operating Revenue")
        operating_income = _flow_sum(
            income,
            statement_date,
            "Operating Income",
            "Total Operating Income As Reported",
        )

        if metric_name == "roe":
            average_equity = _average_balance(
                balance,
                statement_date,
                "Stockholders Equity",
                "Common Stock Equity",
            )
            if net_income is not None and average_equity not in (None, 0):
                value = net_income / average_equity

        elif metric_name == "roic":
            ebit = _flow_sum(income, statement_date, "EBIT")
            if ebit is None:
                ebit = operating_income
            if ebit is None:
                pretax = _flow_sum(income, statement_date, "Pretax Income")
                interest = _flow_sum(
                    income,
                    statement_date,
                    "Interest Expense",
                    "Interest Expense Non Operating",
                )
                if pretax is not None:
                    ebit = pretax + (interest or 0.0)
            invested_capital = _average_invested_capital(balance, statement_date)
            if ebit is not None and invested_capital not in (None, 0):
                nopat = ebit * (1.0 - _effective_tax_rate(income, statement_date))
                value = nopat / invested_capital

        elif metric_name == "debttoequity":
            debt = _latest_balance(balance, statement_date, "Total Debt")
            equity = _latest_balance(
                balance,
                statement_date,
                "Stockholders Equity",
                "Common Stock Equity",
            )
            if debt is not None and equity not in (None, 0):
                value = (debt / equity) * 100.0

        elif metric_name == "profitmargins":
            if net_income is not None and revenue not in (None, 0):
                value = net_income / revenue

        elif metric_name == "operatingmargins":
            if operating_income is not None and revenue not in (None, 0):
                value = operating_income / revenue

        if value is not None and math.isfinite(value):
            values.append(float(value))
            dates.append(statement_date)

    if not values:
        return pd.Series(index=history_index, dtype=float)

    series = pd.Series(values, index=pd.DatetimeIndex(dates)).sort_index()
    history_dates = pd.DatetimeIndex(pd.to_datetime(history_index))
    history_tz = getattr(history_dates, "tz", None)
    if history_tz is not None and series.index.tz is None:
        series.index = series.index.tz_localize(history_tz)
    elif history_tz is None and series.index.tz is not None:
        series.index = series.index.tz_localize(None)

    expanded_index = series.index.union(history_dates).sort_values()
    expanded = series.reindex(expanded_index).ffill()
    return expanded.reindex(history_dates)
