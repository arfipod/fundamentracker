from __future__ import annotations

import logging
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pandas as pd
from fastapi.testclient import TestClient

import api as api_module
from api import app
from market_data.providers import yfinance_provider
from market_data.providers.yfinance_provider import YFinanceProvider
from market_data.service import MarketDataService


NOW = datetime(2026, 5, 8, 12, 0, tzinfo=timezone.utc)
AUTH_HEADER = {"Authorization": "Bearer test-token"}


class FakeSnapshotRepository:
    def __init__(self, *, fresh=None, latest=None, provider_health=None):
        self.fresh = fresh or {}
        self.latest = latest or {}
        self.provider_health = provider_health or []
        self.saved_snapshots = []
        self.health_updates = []
        self.fresh_reads = []
        self.latest_reads = []

    def get_fresh_metric_snapshot(self, symbol, metric, now):
        self.fresh_reads.append((symbol, metric, now))
        return self.fresh.get((symbol, metric))

    def get_latest_metric_snapshot(self, symbol, metric):
        self.latest_reads.append((symbol, metric))
        return self.latest.get((symbol, metric))

    def save_metric_snapshot(self, snapshot):
        self.saved_snapshots.append(snapshot)
        return {"id": "snapshot-1", **snapshot}

    def upsert_provider_health(self, provider, status, **kwargs):
        update = {"provider": provider, "status": status, **kwargs}
        self.health_updates.append(update)
        return update

    def get_provider_health(self):
        return self.provider_health


class FakeProvider:
    source = "fake"

    def __init__(self, *, metric_value=0.125, quote=None, metric_error=None):
        self.metric_value = metric_value
        self.quote = quote or {"symbol": "AAPL", "price": 150.0, "currency": "USD", "source": self.source}
        self.metric_error = metric_error
        self.metric_calls = 0
        self.quote_calls = 0

    def get_quote(self, symbol):
        self.quote_calls += 1
        return {**self.quote, "symbol": symbol}

    def get_metric(self, symbol, metric):
        self.metric_calls += 1
        if self.metric_error:
            raise self.metric_error
        return self.metric_value

    def get_price_history(self, symbol, period):
        raise NotImplementedError

    def get_metric_history(self, symbol, metric, period):
        raise NotImplementedError

    def search_symbols(self, query):
        return []


def test_market_data_service_returns_fresh_cached_metric_without_provider_call():
    repository = FakeSnapshotRepository(
        fresh={
            ("AAPL", "roe"): {
                "symbol": "AAPL",
                "metric": "roe",
                "value": 12.5,
                "source": "yfinance",
                "raw_payload": {"raw_value": 0.125},
            }
        }
    )
    provider = FakeProvider(metric_value=0.3)
    service = MarketDataService(provider, snapshot_repository=repository, clock=lambda: NOW)

    assert service.get_metric("aapl", "roe") == 12.5
    assert service.get_metric("AAPL", "roe", normalized=False) == 0.125
    assert provider.metric_calls == 0
    assert repository.saved_snapshots == []


def test_market_data_service_refreshes_expired_metric_and_records_provider_health():
    repository = FakeSnapshotRepository()
    provider = FakeProvider(metric_value=0.125)
    service = MarketDataService(
        provider,
        snapshot_repository=repository,
        ttl_seconds={"fundamentals": 3600},
        clock=lambda: NOW,
    )

    snapshot = service.get_metric_snapshot("aapl", "roe")

    assert snapshot["value"] == 12.5
    assert snapshot["stale"] is False
    assert provider.metric_calls == 1
    assert repository.saved_snapshots[0]["symbol"] == "AAPL"
    assert repository.saved_snapshots[0]["metric"] == "roe"
    assert repository.saved_snapshots[0]["value"] == 12.5
    assert repository.saved_snapshots[0]["raw_payload"] == {"raw_value": 0.125}
    assert repository.saved_snapshots[0]["expires_at"] == datetime(2026, 5, 8, 13, 0, tzinfo=timezone.utc)
    assert repository.health_updates[0]["provider"] == "fake"
    assert repository.health_updates[0]["status"] == "ok"
    assert repository.health_updates[0]["last_ok_at"] == NOW


def test_market_data_service_returns_stale_metric_when_provider_fails(caplog):
    repository = FakeSnapshotRepository(
        latest={
            ("AAPL", "pe"): {
                "symbol": "AAPL",
                "metric": "pe",
                "value": 18.0,
                "source": "yfinance",
                "fetched_at": "2026-05-08T10:00:00+00:00",
                "expires_at": "2026-05-08T11:00:00+00:00",
                "raw_payload": {"raw_value": 18.0},
            }
        }
    )
    provider = FakeProvider(metric_error=RuntimeError("upstream failed"))
    service = MarketDataService(provider, snapshot_repository=repository, clock=lambda: NOW)

    with caplog.at_level(logging.ERROR):
        snapshot = service.get_metric_snapshot("aapl", "pe")

    assert snapshot["value"] == 18.0
    assert snapshot["stale"] is True
    assert service.get_metric("AAPL", "pe") == 18.0
    assert repository.health_updates[0]["status"] == "error"
    assert repository.health_updates[0]["last_error"] == "upstream failed"
    assert "Provider fake failed while fetching pe for AAPL" in caplog.text


def test_market_data_service_caches_quotes_with_quote_ttl():
    repository = FakeSnapshotRepository()
    provider = FakeProvider(quote={"price": 150.0, "currency": "USD", "regularMarketTime": 1778241600})
    service = MarketDataService(
        provider,
        snapshot_repository=repository,
        ttl_seconds={"quote": 60},
        clock=lambda: NOW,
    )

    quote = service.get_quote("aapl")

    assert quote["symbol"] == "AAPL"
    assert quote["price"] == 150.0
    assert quote["stale"] is False
    assert repository.saved_snapshots[0]["metric"] == "quote"
    assert repository.saved_snapshots[0]["unit"] == "currency"
    assert repository.saved_snapshots[0]["currency"] == "USD"
    assert repository.saved_snapshots[0]["expires_at"] == datetime(2026, 5, 8, 12, 1, tzinfo=timezone.utc)


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
        def get_metric_snapshot(self, symbol, metric):
            assert symbol == "AAPL"
            assert metric == "roe"
            return {
                "value": 12.5,
                "stale": False,
                "source": "fake",
                "as_of_date": "2026-05-08",
                "fetched_at": "2026-05-08T12:00:00+00:00",
                "expires_at": "2026-05-09T12:00:00+00:00",
                "confidence": 0.8,
            }

    monkeypatch.setattr(api_module, "market_data_service", FakeMarketDataService())
    monkeypatch.setenv("API_AUTH_TOKEN", "test-token")

    client = TestClient(app)
    response = client.get("/metric-current?ticker=aapl&metric=roe", headers=AUTH_HEADER)

    assert response.status_code == 200
    assert response.json() == {
        "ticker": "AAPL",
        "metric": "roe",
        "value": 12.5,
        "stale": False,
        "source": "fake",
        "as_of_date": "2026-05-08",
        "fetched_at": "2026-05-08T12:00:00+00:00",
        "expires_at": "2026-05-09T12:00:00+00:00",
        "confidence": 0.8,
    }


def test_provider_health_endpoint_uses_market_data_service(monkeypatch):
    class FakeMarketDataService:
        def get_provider_health(self):
            return [
                {
                    "provider": "yfinance",
                    "status": "ok",
                    "last_ok_at": "2026-05-08T12:00:00+00:00",
                    "last_error_at": None,
                    "last_error": None,
                }
            ]

    monkeypatch.setattr(api_module, "market_data_service", FakeMarketDataService())
    monkeypatch.setenv("API_AUTH_TOKEN", "test-token")

    client = TestClient(app)
    response = client.get("/data/providers/health", headers=AUTH_HEADER)

    assert response.status_code == 200
    assert response.json() == [
        {
            "provider": "yfinance",
            "status": "ok",
            "last_ok_at": "2026-05-08T12:00:00+00:00",
            "last_error_at": None,
            "last_error": None,
        }
    ]
