from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import math
import re
from typing import Any, Mapping

import pandas as pd


@dataclass(frozen=True)
class FundamentalDataPack:
    info: Mapping[str, Any]
    fast_info: Mapping[str, Any]
    ttm_income: pd.DataFrame
    ttm_cash_flow: pd.DataFrame
    quarterly_balance: pd.DataFrame
    annual_income: pd.DataFrame
    annual_cash_flow: pd.DataFrame
    annual_balance: pd.DataFrame


@dataclass(frozen=True)
class DerivedMetricObservation:
    value: float
    as_of_date: date | None
    source_detail: str
    period: str | None
    formula_version: str = "derived_metrics_v1"


VALUATION_LABELS: dict[str, str] = {
    "market_cap": "Market Cap",
    "enterprise_value": "Enterprise Value",
    "pe": "Trailing P/E",
    "fpe": "Forward P/E",
    "peg": "PEG Ratio (5yr expected)",
    "ps": "Price/Sales",
    "pb": "Price/Book",
    "ev_revenue": "Enterprise Value/Revenue",
    "evebitda": "Enterprise Value/EBITDA",
}

VALUATION_CONTEXT_BASE_METRIC: dict[str, str] = {
    "pe_discount_to_median_5y": "pe",
    "pe_percentile_5y": "pe",
    "evebitda_discount_to_median_5y": "evebitda",
    "evebitda_percentile_5y": "evebitda",
}


def _to_float(value: Any) -> float | None:
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
    return numeric if math.isfinite(numeric) else None


def _safe_div(numerator: Any, denominator: Any, *, positive_denominator: bool = False) -> float | None:
    numerator_value = _to_float(numerator)
    denominator_value = _to_float(denominator)
    if numerator_value is None or denominator_value is None or denominator_value == 0:
        return None
    if positive_denominator and denominator_value <= 0:
        return None
    value = numerator_value / denominator_value
    return value if math.isfinite(value) else None


def _normalized_label(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def _statement_series(statement: pd.DataFrame | None, *aliases: str) -> pd.Series:
    if statement is None or statement.empty:
        return pd.Series(dtype=float)

    aliases_normalized = {_normalized_label(alias) for alias in aliases}
    matching_label = next(
        (label for label in statement.index if _normalized_label(label) in aliases_normalized),
        None,
    )
    if matching_label is None:
        return pd.Series(dtype=float)

    row = statement.loc[matching_label]
    if isinstance(row, pd.DataFrame):
        row = row.iloc[0]
    row = pd.to_numeric(row, errors="coerce").dropna()
    if row.empty:
        return pd.Series(dtype=float)

    parsed_index = pd.to_datetime(row.index, errors="coerce")
    valid = ~parsed_index.isna()
    row = row.loc[valid]
    parsed_index = parsed_index[valid]
    if row.empty:
        return pd.Series(dtype=float)
    row.index = parsed_index
    return row.sort_index()


def _latest(statement: pd.DataFrame | None, *aliases: str) -> float | None:
    series = _statement_series(statement, *aliases)
    return _to_float(series.iloc[-1]) if not series.empty else None


def _latest_date(*statements: pd.DataFrame | None) -> date | None:
    dates: list[pd.Timestamp] = []
    for statement in statements:
        if statement is None or statement.empty:
            continue
        parsed = pd.to_datetime(statement.columns, errors="coerce")
        dates.extend(timestamp for timestamp in parsed if not pd.isna(timestamp))
    if not dates:
        return None
    return max(dates).date()


def _mapping_value(mapping: Mapping[str, Any], *keys: str) -> float | None:
    for key in keys:
        try:
            value = mapping.get(key)
        except AttributeError:
            value = None
        numeric = _to_float(value)
        if numeric is not None:
            return numeric
    return None


def _current_price(pack: FundamentalDataPack) -> float | None:
    return _mapping_value(pack.fast_info, "last_price", "lastPrice") or _mapping_value(
        pack.info,
        "currentPrice",
        "regularMarketPrice",
    )


def _shares(pack: FundamentalDataPack) -> float | None:
    return (
        _mapping_value(pack.fast_info, "shares")
        or _mapping_value(pack.info, "sharesOutstanding", "impliedSharesOutstanding")
        or _latest(pack.quarterly_balance, "Ordinary Shares Number", "Share Issued")
    )


def _market_cap(pack: FundamentalDataPack) -> float | None:
    direct = _mapping_value(pack.fast_info, "market_cap", "marketCap") or _mapping_value(
        pack.info,
        "marketCap",
    )
    if direct is not None and direct > 0:
        return direct
    price = _current_price(pack)
    shares = _shares(pack)
    value = _safe_div((price or 0) * (shares or 0), 1) if price and shares else None
    return value if value and value > 0 else None


def _debt(pack: FundamentalDataPack) -> float | None:
    return _latest(pack.quarterly_balance, "Total Debt") or _mapping_value(pack.info, "totalDebt")


def _cash(pack: FundamentalDataPack) -> float | None:
    return (
        _latest(
            pack.quarterly_balance,
            "Cash Cash Equivalents And Short Term Investments",
            "Cash Cash Equivalents and Short Term Investments",
            "Cash And Cash Equivalents",
        )
        or _mapping_value(pack.info, "totalCash")
    )


def _enterprise_value(pack: FundamentalDataPack) -> float | None:
    direct = _mapping_value(pack.info, "enterpriseValue")
    if direct is not None and direct > 0:
        return direct
    market_cap = _market_cap(pack)
    if market_cap is None:
        return None
    debt = _debt(pack) or 0.0
    cash = _cash(pack) or 0.0
    value = market_cap + debt - cash
    return value if value > 0 else None


def _average_balance(statement: pd.DataFrame, *aliases: str) -> float | None:
    series = _statement_series(statement, *aliases)
    if series.empty:
        return None
    current = _to_float(series.iloc[-1])
    if current is None:
        return None
    previous_year = _to_float(series.iloc[-5]) if len(series) >= 5 else None
    if previous_year is None:
        return current
    return (current + previous_year) / 2.0


def _effective_tax_rate(pack: FundamentalDataPack) -> float:
    direct = _latest(pack.ttm_income, "Tax Rate For Calcs")
    if direct is not None and 0 <= direct <= 0.5:
        return direct
    tax = _latest(pack.ttm_income, "Tax Provision")
    pretax = _latest(pack.ttm_income, "Pretax Income")
    calculated = _safe_div(tax, pretax)
    if calculated is not None and 0 <= calculated <= 0.5:
        return calculated
    return 0.21


def _invested_capital_average(pack: FundamentalDataPack) -> float | None:
    direct = _average_balance(pack.quarterly_balance, "Invested Capital")
    if direct is not None and direct > 0:
        return direct

    debt_series = _statement_series(pack.quarterly_balance, "Total Debt")
    equity_series = _statement_series(pack.quarterly_balance, "Stockholders Equity", "Common Stock Equity")
    cash_series = _statement_series(
        pack.quarterly_balance,
        "Cash Cash Equivalents And Short Term Investments",
        "Cash And Cash Equivalents",
    )
    if debt_series.empty and equity_series.empty:
        return None

    dates = sorted(set(debt_series.index) | set(equity_series.index) | set(cash_series.index))
    calculated: list[float] = []
    for timestamp in dates:
        debt = _to_float(debt_series.get(timestamp)) or 0.0
        equity = _to_float(equity_series.get(timestamp)) or 0.0
        cash = _to_float(cash_series.get(timestamp)) or 0.0
        value = debt + equity - cash
        if value > 0:
            calculated.append(value)
    if not calculated:
        return None
    return (calculated[-1] + calculated[-5]) / 2.0 if len(calculated) >= 5 else calculated[-1]


def _annual_growth(statement: pd.DataFrame, *aliases: str) -> float | None:
    series = _statement_series(statement, *aliases)
    if len(series) < 2:
        return None
    current = _to_float(series.iloc[-1])
    previous = _to_float(series.iloc[-2])
    if current is None or previous is None or previous <= 0:
        return None
    return current / previous - 1.0


def _annual_margin_change(
    statement: pd.DataFrame,
    numerator_aliases: tuple[str, ...],
    denominator_aliases: tuple[str, ...],
) -> float | None:
    numerator = _statement_series(statement, *numerator_aliases)
    denominator = _statement_series(statement, *denominator_aliases)
    common_dates = sorted(set(numerator.index) & set(denominator.index))
    if len(common_dates) < 2:
        return None
    previous_date, current_date = common_dates[-2], common_dates[-1]
    previous_margin = _safe_div(numerator.get(previous_date), denominator.get(previous_date))
    current_margin = _safe_div(numerator.get(current_date), denominator.get(current_date))
    if previous_margin is None or current_margin is None:
        return None
    return current_margin - previous_margin


def calculate_derived_metric(metric: str, pack: FundamentalDataPack) -> DerivedMetricObservation | None:
    metric = metric.lower()
    as_of_date = _latest_date(
        pack.ttm_income,
        pack.ttm_cash_flow,
        pack.quarterly_balance,
        pack.annual_income,
        pack.annual_cash_flow,
    )
    market_cap = _market_cap(pack)
    enterprise_value = _enterprise_value(pack)

    revenue = _latest(pack.ttm_income, "Total Revenue", "Operating Revenue")
    gross_profit = _latest(pack.ttm_income, "Gross Profit")
    operating_income = _latest(pack.ttm_income, "Operating Income", "Total Operating Income As Reported")
    ebit = _latest(pack.ttm_income, "EBIT") or operating_income
    ebitda = _latest(pack.ttm_income, "EBITDA", "Normalized EBITDA")
    net_income = _latest(
        pack.ttm_income,
        "Net Income Common Stockholders",
        "Net Income",
        "Net Income From Continuing Operation Net Minority Interest",
    )
    diluted_eps = _latest(pack.ttm_income, "Diluted EPS")
    normalized_eps = _latest(pack.ttm_income, "Normalized Diluted EPS", "Reported Normalized Diluted EPS")
    cfo = _latest(pack.ttm_cash_flow, "Operating Cash Flow")
    fcf = _latest(pack.ttm_cash_flow, "Free Cash Flow")
    capex = _latest(pack.ttm_cash_flow, "Capital Expenditure", "Capital Expenditure Reported")
    sbc = _latest(pack.ttm_cash_flow, "Stock Based Compensation")
    rd = _latest(pack.ttm_income, "Research And Development")
    interest = _latest(pack.ttm_income, "Interest Expense", "Interest Expense Non Operating")
    debt = _debt(pack) or 0.0
    cash = _cash(pack) or 0.0

    if fcf is None and cfo is not None and capex is not None:
        fcf = cfo - abs(capex)

    value: float | None = None
    source_detail = "yfinance statements"
    period: str | None = "TTM"

    if metric == "normalized_pe":
        value = _safe_div(_current_price(pack), normalized_eps, positive_denominator=True)
        if value is None:
            normalized_income = _latest(pack.ttm_income, "Normalized Income")
            value = _safe_div(market_cap, normalized_income, positive_denominator=True)
    elif metric == "ev_to_ebit_ttm":
        value = _safe_div(enterprise_value, ebit, positive_denominator=True)
    elif metric == "price_to_fcf_ttm":
        value = _safe_div(market_cap, fcf, positive_denominator=True)
    elif metric == "fcf_yield_ttm":
        value = _safe_div(fcf, market_cap, positive_denominator=True)
    elif metric == "earnings_yield_ttm":
        value = _safe_div(net_income, market_cap, positive_denominator=True)
    elif metric == "owner_earnings_yield_ttm":
        value = _safe_div((fcf - (sbc or 0.0)) if fcf is not None else None, market_cap, positive_denominator=True)
    elif metric == "roe":
        average_equity = _average_balance(pack.quarterly_balance, "Stockholders Equity", "Common Stock Equity")
        value = _safe_div(net_income, average_equity, positive_denominator=True)
    elif metric == "roic":
        invested_capital = _invested_capital_average(pack)
        nopat = ebit * (1.0 - _effective_tax_rate(pack)) if ebit is not None else None
        value = _safe_div(nopat, invested_capital, positive_denominator=True)
    elif metric == "profitmargins":
        value = _safe_div(net_income, revenue, positive_denominator=True)
    elif metric == "operatingmargins":
        value = _safe_div(operating_income, revenue, positive_denominator=True)
    elif metric == "gross_margin_ttm":
        value = _safe_div(gross_profit, revenue, positive_denominator=True)
    elif metric == "fcf_margin_ttm":
        value = _safe_div(fcf, revenue, positive_denominator=True)
    elif metric == "cfo_to_net_income_ttm":
        value = _safe_div(cfo, net_income)
    elif metric == "fcf_to_net_income_ttm":
        value = _safe_div(fcf, net_income)
    elif metric == "interest_coverage_ttm":
        value = _safe_div(ebit, abs(interest) if interest is not None else None, positive_denominator=True)
    elif metric == "normalized_eps_gap":
        ratio = _safe_div(normalized_eps, diluted_eps)
        value = ratio - 1.0 if ratio is not None else None
    elif metric == "capex_to_revenue_ttm":
        value = _safe_div(abs(capex) if capex is not None else None, revenue, positive_denominator=True)
    elif metric == "sbc_to_revenue_ttm":
        value = _safe_div(sbc, revenue, positive_denominator=True)
    elif metric == "sbc_to_fcf_ttm":
        value = _safe_div(sbc, fcf, positive_denominator=True)
    elif metric == "rd_to_revenue_ttm":
        value = _safe_div(abs(rd) if rd is not None else None, revenue, positive_denominator=True)
    elif metric == "net_debt_to_ebitda_ttm":
        value = _safe_div(debt - cash, ebitda, positive_denominator=True)
    elif metric == "net_cash_to_market_cap":
        value = _safe_div(cash - debt, market_cap, positive_denominator=True)
        period = None
    elif metric == "revenue_growth_yoy":
        value = _annual_growth(pack.annual_income, "Total Revenue", "Operating Revenue")
        period = "FY YoY"
    elif metric == "operating_income_growth_yoy":
        value = _annual_growth(pack.annual_income, "Operating Income", "Total Operating Income As Reported")
        period = "FY YoY"
    elif metric == "diluted_eps_growth_yoy":
        value = _annual_growth(pack.annual_income, "Diluted EPS")
        period = "FY YoY"
    elif metric == "cfo_growth_yoy":
        value = _annual_growth(pack.annual_cash_flow, "Operating Cash Flow")
        period = "FY YoY"
    elif metric == "fcf_growth_yoy":
        value = _annual_growth(pack.annual_cash_flow, "Free Cash Flow")
        period = "FY YoY"
    elif metric == "diluted_share_growth_yoy":
        value = _annual_growth(pack.annual_income, "Diluted Average Shares")
        period = "FY YoY"
    elif metric == "gross_margin_change_yoy":
        value = _annual_margin_change(
            pack.annual_income,
            ("Gross Profit",),
            ("Total Revenue", "Operating Revenue"),
        )
        period = "FY YoY"
    elif metric == "operating_margin_change_yoy":
        value = _annual_margin_change(
            pack.annual_income,
            ("Operating Income", "Total Operating Income As Reported"),
            ("Total Revenue", "Operating Revenue"),
        )
        period = "FY YoY"
    elif metric in {"buyback_yield_ttm", "net_buyback_yield_ttm", "shareholder_yield_ttm"}:
        repurchases = _latest(
            pack.ttm_cash_flow,
            "Repurchase Of Capital Stock",
            "Common Stock Payments",
        )
        issuance = _latest(
            pack.ttm_cash_flow,
            "Issuance Of Capital Stock",
            "Common Stock Issuance",
        )
        dividends = _latest(pack.ttm_cash_flow, "Cash Dividends Paid", "Common Stock Dividend Paid")
        gross_buybacks = abs(repurchases) if repurchases is not None else None
        cash_issuance = abs(issuance) if issuance is not None else 0.0
        cash_dividends = abs(dividends) if dividends is not None else 0.0
        if metric == "buyback_yield_ttm":
            value = _safe_div(gross_buybacks, market_cap, positive_denominator=True)
        elif metric == "net_buyback_yield_ttm":
            value = _safe_div(
                gross_buybacks - cash_issuance if gross_buybacks is not None else None,
                market_cap,
                positive_denominator=True,
            )
        else:
            value = _safe_div(
                gross_buybacks - cash_issuance + cash_dividends if gross_buybacks is not None else None,
                market_cap,
                positive_denominator=True,
            )
    else:
        return None

    if value is None or not math.isfinite(value):
        return None
    return DerivedMetricObservation(
        value=float(value),
        as_of_date=as_of_date,
        source_detail=source_detail,
        period=period,
    )


def valuation_frequency_for_period(period: str) -> str:
    period = period.lower()
    if period in {"1d", "5d", "1mo", "3mo", "6mo", "ytd", "1y"}:
        return "monthly"
    if period in {"2y", "5y"}:
        return "quarterly"
    return "yearly"


def _period_cutoff(period: str, now: pd.Timestamp) -> pd.Timestamp | None:
    period = period.lower()
    offsets: dict[str, pd.DateOffset] = {
        "1d": pd.DateOffset(days=1),
        "5d": pd.DateOffset(days=5),
        "1mo": pd.DateOffset(months=1),
        "3mo": pd.DateOffset(months=3),
        "6mo": pd.DateOffset(months=6),
        "1y": pd.DateOffset(years=1),
        "2y": pd.DateOffset(years=2),
        "5y": pd.DateOffset(years=5),
        "10y": pd.DateOffset(years=10),
    }
    if period == "ytd":
        return pd.Timestamp(year=now.year, month=1, day=1)
    offset = offsets.get(period)
    return now - offset if offset is not None else None


def valuation_history_points(
    valuation: pd.DataFrame,
    metric: str,
    period: str,
    *,
    now: pd.Timestamp | None = None,
) -> list[dict[str, float | str]]:
    label = VALUATION_LABELS.get(metric.lower())
    if label is None or valuation is None or valuation.empty or label not in valuation.index:
        return []

    now = now or pd.Timestamp.now(tz="UTC")
    if now.tzinfo is not None:
        now = now.tz_localize(None)
    cutoff = _period_cutoff(period, now)

    row = valuation.loc[label]
    if isinstance(row, pd.DataFrame):
        row = row.iloc[0]
    points: list[dict[str, float | str]] = []
    for column, raw_value in row.items():
        if str(column) == "Current":
            continue
        timestamp = pd.to_datetime(column, errors="coerce")
        value = _to_float(raw_value)
        if pd.isna(timestamp) or value is None:
            continue
        timestamp = pd.Timestamp(timestamp).tz_localize(None) if pd.Timestamp(timestamp).tzinfo else pd.Timestamp(timestamp)
        if cutoff is not None and timestamp < cutoff:
            continue
        points.append({"date": timestamp.strftime("%Y-%m-%d"), "value": float(value)})
    points.sort(key=lambda point: str(point["date"]))
    return points


def calculate_valuation_context_metric(
    metric: str,
    valuation: pd.DataFrame,
    *,
    now: pd.Timestamp | None = None,
) -> DerivedMetricObservation | None:
    base_metric = VALUATION_CONTEXT_BASE_METRIC.get(metric.lower())
    label = VALUATION_LABELS.get(base_metric or "")
    if label is None or valuation is None or valuation.empty or label not in valuation.index:
        return None

    now = now or pd.Timestamp.now(tz="UTC")
    if now.tzinfo is not None:
        now = now.tz_localize(None)
    cutoff = now - pd.DateOffset(years=5)
    row = valuation.loc[label]
    if isinstance(row, pd.DataFrame):
        row = row.iloc[0]
    current = _to_float(row.get("Current"))
    values: list[float] = []
    for column, raw_value in row.items():
        if str(column) == "Current":
            continue
        timestamp = pd.to_datetime(column, errors="coerce")
        value = _to_float(raw_value)
        if pd.isna(timestamp) or value is None or value <= 0:
            continue
        timestamp = pd.Timestamp(timestamp).tz_localize(None) if pd.Timestamp(timestamp).tzinfo else pd.Timestamp(timestamp)
        if timestamp >= cutoff:
            values.append(value)

    if current is None or current <= 0 or len(values) < 3:
        return None

    if metric.endswith("discount_to_median_5y"):
        median = float(pd.Series(values, dtype=float).median())
        value = _safe_div(current, median, positive_denominator=True)
        value = value - 1.0 if value is not None else None
        detail = f"{label} current versus 5Y median"
    else:
        value = sum(1 for historical in values if historical <= current) / len(values)
        detail = f"{label} 5Y percentile"

    if value is None:
        return None
    return DerivedMetricObservation(
        value=float(value),
        as_of_date=now.date(),
        source_detail=detail,
        period="5Y",
        formula_version="valuation_context_v1",
    )


def calculate_eps_revision_90d(eps_trend: pd.DataFrame) -> DerivedMetricObservation | None:
    if eps_trend is None or eps_trend.empty:
        return None
    preferred_periods = ["+1y", "0y", "+1q", "0q"]
    index_lookup = {_normalized_label(index): index for index in eps_trend.index}
    row = None
    for preferred in preferred_periods:
        actual = index_lookup.get(_normalized_label(preferred))
        if actual is not None:
            row = eps_trend.loc[actual]
            break
    if row is None:
        row = eps_trend.iloc[0]
    current = _to_float(row.get("current"))
    prior = _to_float(row.get("90daysAgo"))
    value = _safe_div(current, prior, positive_denominator=True)
    if value is None:
        return None
    return DerivedMetricObservation(
        value=value - 1.0,
        as_of_date=pd.Timestamp.now(tz="UTC").date(),
        source_detail="yfinance earningsTrend.epsTrend",
        period="90D",
        formula_version="analyst_revision_v1",
    )


def calculate_eps_revision_balance(eps_revisions: pd.DataFrame) -> DerivedMetricObservation | None:
    if eps_revisions is None or eps_revisions.empty:
        return None
    preferred_periods = ["+1y", "0y", "+1q", "0q"]
    index_lookup = {_normalized_label(index): index for index in eps_revisions.index}
    row = None
    for preferred in preferred_periods:
        actual = index_lookup.get(_normalized_label(preferred))
        if actual is not None:
            row = eps_revisions.loc[actual]
            break
    if row is None:
        row = eps_revisions.iloc[0]

    normalized_columns = {_normalized_label(column): column for column in row.index}
    up_column = next((column for key, column in normalized_columns.items() if "up" in key and "30" in key), None)
    down_column = next((column for key, column in normalized_columns.items() if "down" in key and "30" in key), None)
    if up_column is None or down_column is None:
        up_column = next((column for key, column in normalized_columns.items() if "up" in key and "7" in key), None)
        down_column = next((column for key, column in normalized_columns.items() if "down" in key and "7" in key), None)
    up = _to_float(row.get(up_column)) if up_column is not None else None
    down = _to_float(row.get(down_column)) if down_column is not None else None
    if up is None or down is None:
        return None
    return DerivedMetricObservation(
        value=up - down,
        as_of_date=pd.Timestamp.now(tz="UTC").date(),
        source_detail="yfinance earningsTrend.epsRevisions",
        period="30D" if "30" in _normalized_label(up_column) else "7D",
        formula_version="analyst_revision_v1",
    )
