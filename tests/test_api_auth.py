from fastapi.testclient import TestClient

import api as api_module
from api import app


AUTH_HEADER = {"Authorization": "Bearer test-token"}


def test_mutable_endpoints_require_api_token(monkeypatch):
    monkeypatch.setenv("API_AUTH_TOKEN", "test-token")
    monkeypatch.delenv("READONLY_PUBLIC", raising=False)
    client = TestClient(app)

    protected_requests = [
        ("POST", "/add", {"ticker": "AAPL", "metric": "pe", "operator": "<", "value": 20}),
        ("DELETE", "/remove/AAPL", None),
        ("DELETE", "/remove/AAPL/pe", None),
        ("PUT", "/update", {"ticker": "AAPL", "metric": "pe", "value": 18}),
        ("PATCH", "/watchlist/AAPL/metadata", {"status": "researching", "priority": "high"}),
        ("POST", "/watchlist/AAPL/tags", {"name": "core"}),
        ("DELETE", "/watchlist/AAPL/tags/core", None),
        ("PATCH", "/alerts/alert-1", {"value": 18}),
        ("DELETE", "/alerts/alert-1", None),
        ("POST", "/alerts/alert-1/restore", None),
        ("PATCH", "/signals/signal-1/acknowledge", None),
        ("PATCH", "/signals/signal-1/dismiss", None),
        ("POST", "/scan", None),
        ("PUT", "/scan-settings", {"interval_seconds": 3600}),
        ("PATCH", "/alerts/alert-1/toggle", {"is_active": False}),
        ("POST", "/ai-valuation", {"ticker": "AAPL"}),
    ]

    for method, path, payload in protected_requests:
        response = client.request(method, path, json=payload)

        assert response.status_code == 401, f"{method} {path} should require auth"


def test_sensitive_read_endpoints_require_api_token(monkeypatch):
    monkeypatch.setenv("API_AUTH_TOKEN", "test-token")
    monkeypatch.delenv("PUBLIC_READY_HEALTH", raising=False)
    client = TestClient(app)

    protected_requests = [
        "/alert-history",
        "/alerts/deleted",
        "/signals",
        "/tags",
        "/scan-settings",
        "/data/providers/health",
        "/metric-current?ticker=AAPL&metric=pe",
        "/history?ticker=AAPL&metric=pe",
        "/health/ready",
        "/ops/status",
    ]

    for path in protected_requests:
        response = client.get(path)

        assert response.status_code == 401, f"GET {path} should require auth"


def test_metric_catalog_is_public(monkeypatch):
    monkeypatch.setenv("API_AUTH_TOKEN", "test-token")
    client = TestClient(app)

    response = client.get("/metrics/catalog")

    assert response.status_code == 200
    assert any(metric["key"] == "price" for metric in response.json())


def test_invalid_api_token_returns_401(monkeypatch):
    monkeypatch.setenv("API_AUTH_TOKEN", "test-token")
    client = TestClient(app)

    response = client.post("/scan", headers={"Authorization": "Bearer wrong-token"})

    assert response.status_code == 401


def test_valid_api_token_allows_mutable_endpoint(monkeypatch):
    monkeypatch.setenv("API_AUTH_TOKEN", "test-token")
    monkeypatch.setattr(api_module, "perform_scan", lambda: None)
    client = TestClient(app)

    response = client.post("/scan", headers=AUTH_HEADER)

    assert response.status_code == 200
    assert response.json() == {"message": "Scan completed"}


def test_watchlist_is_protected_by_default(monkeypatch):
    monkeypatch.setenv("API_AUTH_TOKEN", "test-token")
    monkeypatch.delenv("READONLY_PUBLIC", raising=False)
    client = TestClient(app)

    response = client.get("/watchlist")

    assert response.status_code == 401


def test_watchlist_accepts_valid_api_token(monkeypatch):
    monkeypatch.setenv("API_AUTH_TOKEN", "test-token")
    monkeypatch.delenv("READONLY_PUBLIC", raising=False)
    monkeypatch.setattr(api_module.db, "get_watchlist", lambda: {"AAPL": {"alerts": []}})
    client = TestClient(app)

    response = client.get("/watchlist", headers=AUTH_HEADER)

    assert response.status_code == 200
    assert response.json() == {"AAPL": {"alerts": []}}


def test_watchlist_can_be_public_readonly(monkeypatch):
    monkeypatch.setenv("API_AUTH_TOKEN", "test-token")
    monkeypatch.setenv("READONLY_PUBLIC", "true")
    monkeypatch.setattr(api_module.db, "get_watchlist", lambda: {"AAPL": {"alerts": []}})
    client = TestClient(app)

    response = client.get("/watchlist")

    assert response.status_code == 200
    assert response.json() == {"AAPL": {"alerts": []}}


def test_health_live_is_public_when_token_is_configured(monkeypatch):
    monkeypatch.setenv("API_AUTH_TOKEN", "test-token")
    client = TestClient(app)

    response = client.get("/health/live")

    assert response.status_code == 200


def test_health_ready_can_be_public_when_enabled(monkeypatch):
    monkeypatch.setenv("API_AUTH_TOKEN", "test-token")
    monkeypatch.setenv("PUBLIC_READY_HEALTH", "true")
    monkeypatch.setattr(
        api_module.db,
        "check_database_connectivity",
        lambda: {"status": "ok", "backend": "postgres"},
    )
    client = TestClient(app)

    response = client.get("/health/ready")

    assert response.status_code == 200


def test_health_ready_accepts_valid_api_token_by_default(monkeypatch):
    monkeypatch.setenv("API_AUTH_TOKEN", "test-token")
    monkeypatch.delenv("PUBLIC_READY_HEALTH", raising=False)
    monkeypatch.setattr(
        api_module.db,
        "check_database_connectivity",
        lambda: {"status": "ok", "backend": "postgres"},
    )
    client = TestClient(app)

    response = client.get("/health/ready", headers=AUTH_HEADER)

    assert response.status_code == 200
