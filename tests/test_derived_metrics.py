from __future__ import annotations

import pandas as pd
import pytest

from market_data.derived_metrics import (
    FundamentalDataPack,
    calculate_derived_metric,
    calculate_eps_revision_90d,
    calculate_eps_revision_balance,
    calculate_valuation_context_metric,
    valuation_history_points,
)


def frame(rows, values, columns):
    return pd.DataFrame(values, index=rows, columns=pd.to_datetime(columns))


def make_pack() -> FundamentalDataPack:
    ttm_income = frame(
        [
            "Total Revenue",
            "Gross Profit",
            "Operating Income",
            "EBIT",
            "EBITDA",
            "Net Income",
            "Diluted EPS",
            "Normalized Diluted EPS",
            "Tax Provision",
            "Pretax Income",
            "Research And Development",
            "Interest Expense",
        ],
        [[200], [160], [80], [80], [100], [60], [24], [26], [12], [72], [30], [2]],
        ["2026-06-30"],
    )
    ttm_cash = frame(
        [
            "Operating Cash Flow",
            "Free Cash Flow",
            "Capital Expenditure",
            "Stock Based Compensation",
            "Repurchase Of Capital Stock",
            "Issuance Of Capital Stock",
            "Cash Dividends Paid",
        ],
        [[120], [50], [-70], [20], [-10], [3], [-2]],
        ["2026-06-30"],
    )
    q_dates = ["2025-06-30", "2025-09-30", "2025-12-31", "2026-03-31", "2026-06-30"]
    q_balance = frame(
        [
            "Invested Capital",
            "Stockholders Equity",
            "Total Debt",
            "Cash Cash Equivalents And Short Term Investments",
            "Ordinary Shares Number",
        ],
        [
            [100, 110, 120, 130, 140],
            [80, 85, 90, 95, 100],
            [90, 92, 95, 98, 100],
            [40, 42, 45, 48, 50],
            [10, 10, 10, 10, 10],
        ],
        q_dates,
    )
    annual_income = frame(
        ["Total Revenue", "Operating Income", "Gross Profit", "Diluted EPS", "Diluted Average Shares"],
        [[150, 180], [50, 72], [105, 135], [18, 22], [9.5, 10]],
        ["2024-12-31", "2025-12-31"],
    )
    annual_cash = frame(
        ["Operating Cash Flow", "Free Cash Flow"],
        [[80, 100], [30, 40]],
        ["2024-12-31", "2025-12-31"],
    )
    return FundamentalDataPack(
        info={"enterpriseValue": 1050},
        fast_info={"last_price": 100, "market_cap": 1000, "shares": 10},
        ttm_income=ttm_income,
        ttm_cash_flow=ttm_cash,
        quarterly_balance=q_balance,
        annual_income=annual_income,
        annual_cash_flow=annual_cash,
        annual_balance=pd.DataFrame(),
    )


def value(metric):
    result = calculate_derived_metric(metric, make_pack())
    assert result is not None
    return result.value


def test_core_valuation_and_cash_metrics():
    assert value("fcf_yield_ttm") == pytest.approx(0.05)
    assert value("price_to_fcf_ttm") == pytest.approx(20)
    assert value("earnings_yield_ttm") == pytest.approx(0.06)
    assert value("owner_earnings_yield_ttm") == pytest.approx(0.03)
    assert value("ev_to_ebit_ttm") == pytest.approx(13.125)
    assert value("normalized_pe") == pytest.approx(100 / 26)


def test_quality_reinvestment_and_leverage_metrics():
    assert value("roe") == pytest.approx(60 / 90)
    assert value("roic") == pytest.approx((80 * (1 - 12 / 72)) / 120)
    assert value("fcf_margin_ttm") == pytest.approx(0.25)
    assert value("sbc_to_revenue_ttm") == pytest.approx(0.10)
    assert value("sbc_to_fcf_ttm") == pytest.approx(0.40)
    assert value("capex_to_revenue_ttm") == pytest.approx(0.35)
    assert value("net_debt_to_ebitda_ttm") == pytest.approx(0.50)
    assert value("net_cash_to_market_cap") == pytest.approx(-0.05)


def test_growth_and_shareholder_metrics():
    assert value("revenue_growth_yoy") == pytest.approx(0.20)
    assert value("operating_income_growth_yoy") == pytest.approx(0.44)
    assert value("diluted_share_growth_yoy") == pytest.approx(10 / 9.5 - 1)
    assert value("gross_margin_change_yoy") == pytest.approx(0.75 - 0.70)
    assert value("buyback_yield_ttm") == pytest.approx(0.01)
    assert value("net_buyback_yield_ttm") == pytest.approx(0.007)
    assert value("shareholder_yield_ttm") == pytest.approx(0.009)


def test_valuation_history_and_context_use_real_period_values():
    valuation = pd.DataFrame(
        {
            "Current": [18.0, 10.0],
            "6/30/2021": [30.0, 16.0],
            "6/30/2022": [24.0, 14.0],
            "6/30/2023": [20.0, 12.0],
            "6/30/2024": [16.0, 10.0],
            "6/30/2025": [14.0, 8.0],
        },
        index=["Trailing P/E", "Enterprise Value/EBITDA"],
    )
    now = pd.Timestamp("2026-07-01")
    points = valuation_history_points(valuation, "pe", "5y", now=now)
    assert points == [
        {"date": "2022-06-30", "value": 24.0},
        {"date": "2023-06-30", "value": 20.0},
        {"date": "2024-06-30", "value": 16.0},
        {"date": "2025-06-30", "value": 14.0},
    ]
    discount = calculate_valuation_context_metric("pe_discount_to_median_5y", valuation, now=now)
    percentile = calculate_valuation_context_metric("pe_percentile_5y", valuation, now=now)
    assert discount is not None and discount.value == pytest.approx(18 / 18 - 1)
    assert percentile is not None and percentile.value == pytest.approx(2 / 4)


def test_analyst_revision_helpers():
    trend = pd.DataFrame(
        {"current": [12.0], "90daysAgo": [10.0]},
        index=["+1y"],
    )
    revisions = pd.DataFrame(
        {"upLast30days": [8], "downLast30Days": [3]},
        index=["+1y"],
    )
    trend_result = calculate_eps_revision_90d(trend)
    balance_result = calculate_eps_revision_balance(revisions)
    assert trend_result is not None and trend_result.value == pytest.approx(0.20)
    assert balance_result is not None and balance_result.value == 5
