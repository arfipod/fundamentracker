from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

import api as api_module
from api import app


AUTH_HEADER = {"Authorization": "Bearer test-token"}


class FakeMarketDataService:
    def search_symbols(self, query):
        return [{"symbol": query.upper(), "name": "Example Co"}]

    def get_provider_health(self):
        return [{"provider": "fake", "status": "ok"}]

    def get_metric_snapshot(self, symbol, metric):
        return {
            "value": 12.5,
            "stale": False,
            "source": "fake",
            "as_of_date": "2026-05-08",
            "fetched_at": "2026-05-08T12:00:00+00:00",
            "expires_at": "2026-05-08T12:01:00+00:00",
            "confidence": 0.8,
        }

    def get_metric_history(self, symbol, metric, period):
        return [{"date": "2026-05-08", "value": 12.5}]

    def get_price_history(self, symbol, period):
        return [
            {"date": "2026-05-07", "value": 100.0},
            {"date": "2026-05-08", "value": 101.0},
        ]

    def get_quote(self, symbol):
        return {"shortName": "Example Co"}

    def get_metric(self, symbol, metric):
        return 10.0


def test_api_api_app_importable():
    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root)

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from api.api import app; print(app.title)",
        ],
        cwd=repo_root,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "FundamenTracker API"


def test_registered_route_smoke_table():
    actual = {
        (method, route.path)
        for route in app.routes
        for method in getattr(route, "methods", set())
        if method not in {"HEAD", "OPTIONS"}
    }

    expected = {
        ("GET", "/health/live"),
        ("GET", "/health/ready"),
        ("POST", "/ai-valuation"),
        ("GET", "/watchlist"),
        ("POST", "/add"),
        ("DELETE", "/remove/{ticker}"),
        ("DELETE", "/remove/{ticker}/{metric}"),
        ("PUT", "/update"),
        ("PATCH", "/alerts/{alert_id}"),
        ("DELETE", "/alerts/{alert_id}"),
        ("GET", "/alerts/deleted"),
        ("POST", "/alerts/{alert_id}/restore"),
        ("PATCH", "/alerts/{alert_id}/toggle"),
        ("GET", "/alert-history"),
        ("GET", "/signals"),
        ("PATCH", "/signals/{signal_id}/acknowledge"),
        ("PATCH", "/signals/{signal_id}/dismiss"),
        ("POST", "/scan"),
        ("GET", "/scan-settings"),
        ("PUT", "/scan-settings"),
        ("GET", "/server-time"),
        ("GET", "/search"),
        ("GET", "/data/providers/health"),
        ("GET", "/metrics/catalog"),
        ("GET", "/fundamentals/sec/{ticker}"),
        ("GET", "/metric-current"),
        ("GET", "/history"),
        ("GET", "/market-overview"),
        ("GET", "/ops/status"),
    }

    assert expected <= actual


def test_route_smoke_responses(monkeypatch):
    monkeypatch.setenv("API_AUTH_TOKEN", "test-token")
    monkeypatch.setattr(api_module, "market_data_service", FakeMarketDataService())
    monkeypatch.setattr(
        api_module.db,
        "get_scan_settings_db",
        lambda: {"interval_seconds": 0, "last_scan_time": 0},
    )
    monkeypatch.setattr(
        api_module.db,
        "get_alert_history_db",
        lambda limit=50: [{"id": "history-1", "limit": limit}],
    )
    monkeypatch.setattr(
        api_module.db,
        "get_deleted_alerts_db",
        lambda: [{"id": "deleted-alert"}],
    )
    monkeypatch.setattr(
        api_module.db,
        "get_signals",
        lambda status="open", limit=50: [{"id": "signal-1", "status": status, "limit": limit}],
    )

    client = TestClient(app)

    assert client.get("/health/live").status_code == 200
    assert "server_time" in client.get("/server-time").json()
    assert client.get("/search?q=aapl").json() == [{"symbol": "AAPL", "name": "Example Co"}]
    assert client.get("/scan-settings", headers=AUTH_HEADER).json() == {
        "interval_seconds": 0,
        "last_scan_time": 0,
    }
    assert client.get("/alert-history?limit=1", headers=AUTH_HEADER).json() == [
        {"id": "history-1", "limit": 1}
    ]
    assert client.get("/alerts/deleted", headers=AUTH_HEADER).json() == [{"id": "deleted-alert"}]
    assert client.get("/signals?status=open&limit=1", headers=AUTH_HEADER).json() == [
        {"id": "signal-1", "status": "open", "limit": 1}
    ]
    assert client.get("/data/providers/health", headers=AUTH_HEADER).json() == [
        {"provider": "fake", "status": "ok"}
    ]
    catalog = client.get("/metrics/catalog").json()
    assert {metric["key"] for metric in catalog} >= {"pe", "fpe", "pb", "evebitda", "roe", "price"}
    assert catalog == sorted(catalog, key=lambda metric: (metric["category"], metric["label"]))
    assert client.get(
        "/metric-current?ticker=aapl&metric=roe",
        headers=AUTH_HEADER,
    ).json()["ticker"] == "AAPL"
    assert client.get("/history?ticker=aapl&metric=roe", headers=AUTH_HEADER).json() == [
        {"date": "2026-05-08", "value": 12.5}
    ]
    assert client.get("/market-overview").json() == [
        {"symbol": "SPY", "current": 101.0, "change_percent": 1.0},
        {"symbol": "QQQ", "current": 101.0, "change_percent": 1.0},
        {"symbol": "DIA", "current": 101.0, "change_percent": 1.0},
    ]


def test_mutable_route_smoke_responses(monkeypatch):
    monkeypatch.setenv("API_AUTH_TOKEN", "test-token")
    monkeypatch.setattr(api_module, "market_data_service", FakeMarketDataService())
    monkeypatch.setattr(api_module, "perform_scan", lambda: None)
    monkeypatch.setattr(api_module.db, "add_ticker_db", lambda symbol, name: [{"symbol": symbol}])
    monkeypatch.setattr(
        api_module.db,
        "add_alert_db",
        lambda symbol, metric, operator, target, alert_type, reference_value: [{"id": "alert-1"}],
    )
    monkeypatch.setattr(
        api_module.db,
        "update_scan_settings_db",
        lambda interval=None, last_scan_time=None: {"interval_seconds": interval or 0, "last_scan_time": 0},
    )
    monkeypatch.setattr(
        api_module.db,
        "get_scan_settings_db",
        lambda: {"interval_seconds": 60, "last_scan_time": 0},
    )

    signals = [
        {
            "id": "signal-1",
            "title": "AAPL PE crossed below 20",
            "acknowledged_at": None,
            "dismissed_at": None,
        }
    ]

    def get_signals(status="open", limit=50):
        rows = signals
        if status == "open":
            rows = [
                signal
                for signal in rows
                if signal.get("acknowledged_at") is None and signal.get("dismissed_at") is None
            ]
        return rows[:limit]

    def acknowledge_signal(signal_id):
        for signal in signals:
            if signal["id"] == signal_id:
                signal["acknowledged_at"] = "2026-05-08T12:00:00+00:00"
                return signal
        return None

    monkeypatch.setattr(api_module.db, "get_signals", get_signals)
    monkeypatch.setattr(api_module.db, "acknowledge_signal", acknowledge_signal)
    monkeypatch.setattr(api_module.db, "dismiss_signal", lambda signal_id: None)

    client = TestClient(app)

    add_response = client.post(
        "/add",
        headers=AUTH_HEADER,
        json={"ticker": "aapl", "metric": "pe", "operator": "<", "value": 20},
    )
    assert add_response.status_code == 200
    assert add_response.json()["ticker"] == "AAPL"

    scan_response = client.post("/scan", headers=AUTH_HEADER)
    assert scan_response.status_code == 200
    assert scan_response.json() == {"message": "Scan completed"}

    settings_response = client.put(
        "/scan-settings",
        headers=AUTH_HEADER,
        json={"interval_seconds": 60},
    )
    assert settings_response.status_code == 200
    assert settings_response.json() == {"interval_seconds": 60, "last_scan_time": 0}

    assert client.get("/signals", headers=AUTH_HEADER).json() == [
        {
            "id": "signal-1",
            "title": "AAPL PE crossed below 20",
            "acknowledged_at": None,
            "dismissed_at": None,
        }
    ]

    ack_response = client.patch("/signals/signal-1/acknowledge", headers=AUTH_HEADER)
    assert ack_response.status_code == 200
    assert ack_response.json()["acknowledged_at"] == "2026-05-08T12:00:00+00:00"
    assert client.get("/signals", headers=AUTH_HEADER).json() == []
