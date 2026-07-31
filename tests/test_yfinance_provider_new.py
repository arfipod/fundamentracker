from __future__ import annotations

import pandas as pd
import pytest

from market_data.providers import yfinance_provider
from market_data.providers.yfinance_provider import YFinanceProvider


def test_current_metrics_use_fast_info_and_normalize_upstream_in_service_layer(monkeypatch):
    class FastInfo(dict):
        pass

    class FakeTicker:
        info = {
            "currentPrice": 150,
            "returnOnEquity": 0.125,
            "dividendYield": 0.021,
            "payoutRatio": 0.35,
        }
        fast_info = FastInfo(last_price=151, market_cap=1000, shares=10)
        ttm_income_stmt = pd.DataFrame()
        ttm_cash_flow = pd.DataFrame()
        quarterly_balance_sheet = pd.DataFrame()
        income_stmt = pd.DataFrame()
        cash_flow = pd.DataFrame()
        balance_sheet = pd.DataFrame()

    monkeypatch.setattr(yfinance_provider.yf, "Ticker", lambda _symbol: FakeTicker())
    provider = YFinanceProvider(cache_ttl_seconds=0)

    assert provider.get_metric("aapl", "price") == 151
    assert provider.get_metric("aapl", "market_cap") == 1000
    assert provider.get_metric("aapl", "dividendyield") == pytest.approx(0.021)


def test_metric_history_uses_real_yahoo_valuation_table(monkeypatch):
    valuation = pd.DataFrame(
        {
            "Current": [21.0],
            "1/31/2024": [20.0],
            "2/29/2024": [22.0],
        },
        index=["Trailing P/E"],
    )

    class FakeTicker:
        info = {"trailingEps": 5.0}

        def get_valuation_measures(self, freq, periods):
            assert freq == "yearly"
            assert periods is None
            return valuation

    monkeypatch.setattr(yfinance_provider.yf, "Ticker", lambda _symbol: FakeTicker())
    provider = YFinanceProvider(cache_ttl_seconds=0)

    assert provider.get_metric_history("AAPL", "pe", "max") == [
        {"date": "2024-01-31", "value": 20.0},
        {"date": "2024-02-29", "value": 22.0},
    ]


def test_statement_derived_metric_observation_contains_metadata(monkeypatch):
    date = pd.Timestamp("2026-06-30")

    class FakeTicker:
        info = {"marketCap": 1000, "currentPrice": 100}
        fast_info = {"market_cap": 1000, "last_price": 100, "shares": 10}
        ttm_income_stmt = pd.DataFrame(
            {date: [200, 60]},
            index=["Total Revenue", "Net Income"],
        )
        ttm_cash_flow = pd.DataFrame(
            {date: [50]},
            index=["Free Cash Flow"],
        )
        quarterly_balance_sheet = pd.DataFrame()
        income_stmt = pd.DataFrame()
        cash_flow = pd.DataFrame()
        balance_sheet = pd.DataFrame()

    monkeypatch.setattr(yfinance_provider.yf, "Ticker", lambda _symbol: FakeTicker())
    provider = YFinanceProvider(cache_ttl_seconds=0)

    observation = provider.get_metric_observation("META", "fcf_yield_ttm")

    assert observation is not None
    assert observation["value"] == pytest.approx(0.05)
    assert observation["period"] == "TTM"
    assert observation["as_of_date"].isoformat() == "2026-06-30"
    assert observation["formula_version"] == "derived_metrics_v1"


def test_historical_roe_uses_ttm_window(monkeypatch):
    dates = pd.to_datetime(["2025-03-31", "2025-06-30", "2025-09-30", "2025-12-31", "2026-03-31"])
    history = pd.DataFrame({"Close": [100, 101, 102, 103, 104]}, index=dates)

    class FakeTicker:
        info = {}
        quarterly_incomestmt = pd.DataFrame(
            {date: [10.0] for date in dates},
            index=["Net Income"],
        )
        quarterly_balancesheet = pd.DataFrame(
            {date: [100.0 + index * 10] for index, date in enumerate(dates)},
            index=["Stockholders Equity"],
        )

        def history(self, period):
            assert period == "2y"
            return history

    monkeypatch.setattr(yfinance_provider.yf, "Ticker", lambda _symbol: FakeTicker())
    provider = YFinanceProvider(cache_ttl_seconds=0)

    points = provider.get_metric_history("AAPL", "roe", "2y")

    assert points[-1]["value"] == pytest.approx((40 / 120) * 100)
