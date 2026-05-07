from __future__ import annotations

from copy import deepcopy
from unittest.mock import MagicMock

import pandas as pd
from fastapi.testclient import TestClient

import api as api_module
import scanner
from api import app
from market_data.normalizers import normalize_metric_value
from market_data.providers import yfinance_provider
from market_data.providers.yfinance_provider import YFinanceProvider
from market_data.service import MarketDataService


def test_normalize_metric_value_uses_metric_definition_multiplier():
    assert normalize_metric_value("roe", 0.1234) == 12.34
    assert normalize_metric_value("profitmargins", 0.25) == 25.0
    assert normalize_metric_value("dividendyield", 0.021) == 2.1
    assert normalize_metric_value("payoutratio", 0.35) == 35.0
    assert normalize_metric_value("pe", 18.5) == 18.5


def test_yfinance_provider_current_metrics_are_normalized(monkeypatch):
    class FakeTicker:
        info = {
            "currentPrice": 150,
            "returnOnEquity": 0.125,
            "dividendYield": 0.021,
            "payoutRatio": 0.35,
        }

    mock_ticker = MagicMock(return_value=FakeTicker())
    monkeypatch.setattr(yfinance_provider.yf, "Ticker", mock_ticker)

    service = MarketDataService(YFinanceProvider(cache_ttl_seconds=0))

    assert service.get_metric("aapl", "price") == 150.0
    assert service.get_metric("AAPL", "roe") == 12.5
    assert service.get_metric("AAPL", "roe", normalized=False) == 0.125
    assert service.get_metric("AAPL", "dividendyield") == 2.1
    assert service.get_metric("AAPL", "payoutratio") == 35.0


def test_yfinance_provider_metric_history_calculates_pe_from_mocked_history(monkeypatch):
    dates = pd.to_datetime(["2024-01-02", "2024-01-03"])
    history = pd.DataFrame({"Close": [100.0, 110.0]}, index=dates)

    class FakeTicker:
        info = {"trailingEps": 5.0}

        def history(self, period):
            assert period == "1mo"
            return history

    monkeypatch.setattr(yfinance_provider.yf, "Ticker", lambda _symbol: FakeTicker())

    service = MarketDataService(YFinanceProvider(cache_ttl_seconds=0))

    assert service.get_metric_history("AAPL", "pe", "1mo") == [
        {"date": "2024-01-02", "value": 20.0},
        {"date": "2024-01-03", "value": 22.0},
    ]


def test_yfinance_provider_metric_history_normalizes_fundamental_series(monkeypatch):
    dates = pd.to_datetime(["2024-03-31", "2024-04-01"])
    history = pd.DataFrame({"Close": [100.0, 101.0]}, index=dates)
    statement_date = pd.Timestamp("2024-03-31")

    class FakeTicker:
        info = {}
        quarterly_incomestmt = pd.DataFrame(
            {statement_date: [20.0]},
            index=["Net Income"],
        )
        quarterly_balancesheet = pd.DataFrame(
            {statement_date: [100.0]},
            index=["Stockholders Equity"],
        )

        def history(self, period):
            assert period == "1y"
            return history

    monkeypatch.setattr(yfinance_provider.yf, "Ticker", lambda _symbol: FakeTicker())

    service = MarketDataService(YFinanceProvider(cache_ttl_seconds=0))

    assert service.get_metric_history("AAPL", "roe", "1y") == [
        {"date": "2024-03-31", "value": 20.0},
        {"date": "2024-04-01", "value": 20.0},
    ]


def test_metric_current_endpoint_uses_market_data_service(monkeypatch):
    class FakeMarketDataService:
        def get_metric(self, symbol, metric):
            assert symbol == "AAPL"
            assert metric == "roe"
            return 12.5

    monkeypatch.setattr(api_module, "market_data_service", FakeMarketDataService())

    client = TestClient(app)
    response = client.get("/metric-current?ticker=aapl&metric=roe")

    assert response.status_code == 200
    assert response.json() == {"ticker": "AAPL", "metric": "roe", "value": 12.5}


def test_scanner_uses_injected_market_data_service(monkeypatch):
    state = {
        "AAPL": {
            "name": "Apple Inc.",
            "alerts": [
                {
                    "id": "alert-1",
                    "metric": "pe",
                    "operator": "<",
                    "target": 20.0,
                    "is_active": True,
                    "is_triggered": False,
                    "reference_value": None,
                    "alert_type": "absolute",
                }
            ],
        }
    }
    updates = []
    history = []

    class FakeMarketDataService:
        def get_metric(self, symbol, metric):
            assert symbol == "AAPL"
            assert metric == "pe"
            return 18.0

    monkeypatch.setattr(scanner.db, "get_watchlist", lambda: deepcopy(state))
    monkeypatch.setattr(
        scanner.db,
        "update_alert_status",
        lambda alert_id, is_triggered, current_value: updates.append(
            (alert_id, is_triggered, current_value)
        ),
    )
    monkeypatch.setattr(
        scanner.db,
        "log_alert_history",
        lambda alert_id, current_value, target: history.append((alert_id, current_value, target)),
    )

    send_alert = MagicMock()

    scanner.run_fundamental_scan(send_alert, market_data_service=FakeMarketDataService())

    assert updates == [("alert-1", True, 18.0)]
    assert history == [("alert-1", 18.0, 20.0)]
    send_alert.assert_called_once()
