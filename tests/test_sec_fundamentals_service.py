from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

import api as api_module
from api import app
from market_data.providers.sec_edgar_provider import SecConceptNotFoundError, SecTickerNotFoundError
from services import market as market_service


AUTH_HEADER = {"Authorization": "Bearer test-token"}
NOW = datetime(2026, 5, 8, 12, 0, tzinfo=timezone.utc)


class FakeSecProvider:
    def __init__(self, *, missing_metrics: set[str] | None = None, missing_ticker: bool = False):
        self.missing_metrics = missing_metrics or set()
        self.missing_ticker = missing_ticker

    def ticker_to_cik(self, symbol):
        if self.missing_ticker:
            raise SecTickerNotFoundError(symbol)
        return "0000320193"

    def get_company_facts(self, cik):
        return {"entityName": "Apple Inc."}

    def get_metric_snapshot(self, symbol, metric):
        if metric in self.missing_metrics:
            raise SecConceptNotFoundError(symbol, metric)
        return {
            "symbol": symbol,
            "cik": "0000320193",
            "company_name": "Apple Inc.",
            "source": "sec",
            "metric": metric,
            "value": 1000.0,
            "unit": "USD",
            "concept": "Revenues",
            "label": "Revenue",
            "fiscal_year": 2025,
            "fiscal_period": "FY",
            "form": "10-K",
            "as_of_date": "2025-09-30",
            "filed_at": "2025-11-01",
            "accession": "0000320193-25-000001",
            "fetched_at": "2026-05-08T12:00:00+00:00",
        }


class FakeRepository:
    def __init__(self):
        self.saved_snapshots = []
        self.health_updates = []

    def save_metric_snapshot(self, snapshot):
        self.saved_snapshots.append(snapshot)
        return {"id": "snapshot-1", **snapshot}

    def upsert_provider_health(self, provider, status, **kwargs):
        self.health_updates.append({"provider": provider, "status": status, **kwargs})


def test_sec_fundamentals_returns_facts_caches_snapshots_and_keeps_optional_errors():
    repository = FakeRepository()
    provider = FakeSecProvider(missing_metrics={"capex"})

    response = market_service.get_sec_fundamentals(
        "aapl",
        provider=provider,
        snapshot_repository=repository,
        clock=lambda: NOW,
    )

    assert response["ticker"] == "AAPL"
    assert response["cik"] == "0000320193"
    assert response["company_name"] == "Apple Inc."
    assert {fact["metric"] for fact in response["facts"]} >= {"revenue", "net_income"}
    assert {error["metric"] for error in response["errors"]} == {"capex"}

    revenue = response["facts"][0]
    assert revenue == {
        "metric": "revenue",
        "value": 1000.0,
        "unit": "USD",
        "concept": "Revenues",
        "label": "Revenue",
        "fiscal_year": 2025,
        "fiscal_period": "FY",
        "form": "10-K",
        "as_of_date": "2025-09-30",
        "filed_at": "2025-11-01",
        "accession": "0000320193-25-000001",
        "source": "sec",
    }
    assert repository.saved_snapshots[0]["symbol"] == "AAPL"
    assert repository.saved_snapshots[0]["metric"] == "revenue"
    assert repository.saved_snapshots[0]["source"] == "sec"
    assert repository.saved_snapshots[0]["raw_payload"]["accession"] == "0000320193-25-000001"
    assert repository.health_updates[-1] == {
        "provider": "sec",
        "status": "ok",
        "last_ok_at": NOW,
    }


def test_sec_fundamentals_missing_mapping_returns_unavailable_payload():
    repository = FakeRepository()

    response = market_service.get_sec_fundamentals(
        "asml",
        provider=FakeSecProvider(missing_ticker=True),
        snapshot_repository=repository,
        clock=lambda: NOW,
    )

    assert response["ticker"] == "ASML"
    assert response["cik"] is None
    assert response["facts"] == []
    assert "No SEC CIK mapping found" in response["errors"][0]["message"]
    assert repository.saved_snapshots == []
    assert repository.health_updates[-1]["status"] == "ok"


def test_sec_fundamentals_endpoint_uses_fake_sec_provider_without_live_requests(monkeypatch):
    repository = FakeRepository()
    monkeypatch.setenv("API_AUTH_TOKEN", "test-token")
    monkeypatch.setattr(market_service, "SecEdgarProvider", lambda: FakeSecProvider())
    monkeypatch.setattr(market_service, "get_repository", lambda: repository)

    client = TestClient(app)
    response = client.get("/fundamentals/sec/aapl", headers=AUTH_HEADER)

    assert response.status_code == 200
    body = response.json()
    assert body["ticker"] == "AAPL"
    assert body["cik"] == "0000320193"
    assert body["facts"][0]["source"] == "sec"
    assert repository.saved_snapshots[0]["source"] == "sec"


def test_sec_fundamentals_endpoint_is_protected(monkeypatch):
    monkeypatch.setenv("API_AUTH_TOKEN", "test-token")

    client = TestClient(api_module.app)
    response = client.get("/fundamentals/sec/aapl")

    assert response.status_code == 401
