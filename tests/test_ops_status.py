from __future__ import annotations

from fastapi.testclient import TestClient

import api as api_module
from api import app
from services import ops as ops_service


AUTH_HEADER = {"Authorization": "Bearer test-token"}
FIXED_NOW = "2026-05-08T12:00:00+00:00"


class FakeDatabase:
    DatabaseHealthError = api_module.db.DatabaseHealthError

    def __init__(
        self,
        *,
        database: dict | None = None,
        scan_settings: dict | None = None,
        database_error: Exception | None = None,
        scan_error: Exception | None = None,
    ):
        self.database = database or {"status": "ok", "backend": "postgres"}
        self.scan_settings = scan_settings or {
            "interval_seconds": 300,
            "last_scan_time": 1778241600,
        }
        self.database_error = database_error
        self.scan_error = scan_error

    def check_database_connectivity(self):
        if self.database_error:
            raise self.database_error
        return self.database

    def get_scan_settings_db(self):
        if self.scan_error:
            raise self.scan_error
        return self.scan_settings


class FakeMarketDataService:
    def __init__(self, provider_health=None, error: Exception | None = None):
        self.provider_health = provider_health if provider_health is not None else []
        self.error = error

    def get_provider_health(self):
        if self.error:
            raise self.error
        return self.provider_health


def test_ops_status_returns_consolidated_operational_payload(monkeypatch):
    monkeypatch.setenv("API_AUTH_TOKEN", "test-token")
    monkeypatch.setattr(
        api_module,
        "db",
        FakeDatabase(
            scan_settings={
                "interval_seconds": 300,
                "last_scan_time": 1778241600,
            }
        ),
    )
    monkeypatch.setattr(
        api_module,
        "market_data_service",
        FakeMarketDataService(
            [
                {
                    "provider": "yfinance",
                    "status": "ok",
                    "last_ok_at": FIXED_NOW,
                    "last_error_at": None,
                    "last_error": "do not echo arbitrary upstream error text",
                }
            ]
        ),
    )
    client = TestClient(app)

    response = client.get("/ops/status", headers=AUTH_HEADER)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["api"] == {
        "status": "ok",
        "service": "fundamentracker-api",
    }
    assert body["database"] == {
        "status": "ok",
        "backend": "postgres",
        "ready": True,
    }
    assert body["provider_health"] == {
        "status": "ok",
        "providers": [
            {
                "provider": "yfinance",
                "status": "ok",
                "last_ok_at": FIXED_NOW,
                "last_error_at": None,
                "has_error": True,
            }
        ],
    }
    assert body["scan"] == {
        "interval_seconds": 300,
        "last_scan_time": 1778241600,
        "last_scan_at": FIXED_NOW,
    }
    assert "server_time" in body
    assert "last_error" not in body["provider_health"]["providers"][0]


def test_ops_status_handles_empty_provider_health(monkeypatch):
    monkeypatch.setenv("API_AUTH_TOKEN", "test-token")
    monkeypatch.setattr(api_module, "db", FakeDatabase())
    monkeypatch.setattr(api_module, "market_data_service", FakeMarketDataService([]))
    client = TestClient(app)

    response = client.get("/ops/status", headers=AUTH_HEADER)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["provider_health"] == {"status": "unknown", "providers": []}


def test_ops_status_is_degraded_when_provider_health_reports_errors(monkeypatch):
    monkeypatch.setenv("API_AUTH_TOKEN", "test-token")
    monkeypatch.setattr(api_module, "db", FakeDatabase())
    monkeypatch.setattr(
        api_module,
        "market_data_service",
        FakeMarketDataService([{"provider": "yfinance", "status": "error"}]),
    )
    client = TestClient(app)

    response = client.get("/ops/status", headers=AUTH_HEADER)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["provider_health"]["status"] == "error"


def test_ops_status_reports_database_failure_without_exposing_secrets(monkeypatch):
    monkeypatch.setenv("API_AUTH_TOKEN", "test-token")
    database_error = api_module.db.DatabaseHealthError(
        reason="connection_failed",
        detail="PostgreSQL readiness check failed.",
        backend="postgres",
    )
    monkeypatch.setattr(
        api_module,
        "db",
        FakeDatabase(
            database_error=database_error,
            scan_error=RuntimeError("scan settings unavailable"),
        ),
    )
    monkeypatch.setattr(api_module, "market_data_service", FakeMarketDataService([]))
    client = TestClient(app)

    response = client.get("/ops/status", headers=AUTH_HEADER)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["database"] == {
        "status": "error",
        "ready": False,
        "backend": "postgres",
        "reason": "connection_failed",
        "detail": "PostgreSQL readiness check failed.",
    }
    assert body["scan"] == {
        "interval_seconds": None,
        "last_scan_time": None,
        "last_scan_at": None,
        "status": "unavailable",
    }


def test_ops_status_service_includes_version_when_available():
    payload = ops_service.status_payload(
        db_client=FakeDatabase(),
        market_data_service=FakeMarketDataService([]),
        service_name="fundamentracker-api",
        service_version="1.2.3",
        timestamp_fn=lambda: FIXED_NOW,
    )

    assert payload["api"]["version"] == "1.2.3"
    assert payload["server_time"] == FIXED_NOW
