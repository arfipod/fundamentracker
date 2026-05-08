from fastapi.testclient import TestClient

import api as api_module
from api import app


def test_health_live():
    client = TestClient(app)

    response = client.get("/health/live")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "fundamentracker-api"
    assert "timestamp" in body


def test_health_ready_ok(monkeypatch):
    client = TestClient(app)

    def fake_check_database_connectivity():
        return {"status": "ok", "backend": "supabase_rest"}

    monkeypatch.setattr(api_module.db, "check_database_connectivity", fake_check_database_connectivity)

    response = client.get("/health/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "fundamentracker-api"
    assert body["checks"]["configuration"]["status"] == "ok"
    assert body["checks"]["database"] == {"status": "ok", "backend": "supabase_rest"}
    assert "timestamp" in body


def test_health_ready_returns_503_for_database_failure(monkeypatch):
    client = TestClient(app)

    def fake_check_database_connectivity():
        raise api_module.db.DatabaseHealthError(
            reason="not_configured",
            detail="SUPABASE_URL and SUPABASE_KEY must be configured.",
        )

    monkeypatch.setattr(api_module.db, "check_database_connectivity", fake_check_database_connectivity)

    response = client.get("/health/ready")

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["status"] == "error"
    assert detail["service"] == "fundamentracker-api"
    assert detail["checks"]["database"] == {
        "status": "error",
        "backend": "supabase_rest",
        "reason": "not_configured",
        "detail": "SUPABASE_URL and SUPABASE_KEY must be configured.",
    }
    assert "timestamp" in detail


def test_health_ready_error_reports_selected_backend(monkeypatch):
    client = TestClient(app)

    def fake_check_database_connectivity():
        raise api_module.db.DatabaseHealthError(
            reason="connection_failed",
            detail="PostgreSQL readiness check failed.",
            backend="postgres",
        )

    monkeypatch.setattr(api_module.db, "check_database_connectivity", fake_check_database_connectivity)

    response = client.get("/health/ready")

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["checks"]["database"] == {
        "status": "error",
        "backend": "postgres",
        "reason": "connection_failed",
        "detail": "PostgreSQL readiness check failed.",
    }
