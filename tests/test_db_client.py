import pytest

from db import client as db


def test_database_backend_defaults_to_supabase_rest(monkeypatch):
    monkeypatch.delenv("DATABASE_BACKEND", raising=False)

    assert db.get_database_backend() == "supabase_rest"


def test_database_backend_accepts_postgresql_alias(monkeypatch):
    monkeypatch.setenv("DATABASE_BACKEND", "PostgreSQL")

    assert db.get_database_backend() == "postgres"
    assert db.is_postgres_backend() is True


def test_check_database_connectivity_rejects_unknown_backend(monkeypatch):
    monkeypatch.setenv("DATABASE_BACKEND", "sqlite")

    with pytest.raises(db.DatabaseHealthError) as exc_info:
        db.check_database_connectivity()

    assert exc_info.value.reason == "unsupported_backend"
    assert exc_info.value.backend == "sqlite"


def test_postgres_health_requires_database_url(monkeypatch):
    monkeypatch.setenv("DATABASE_BACKEND", "postgres")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(db.DatabaseHealthError) as exc_info:
        db.check_database_connectivity()

    assert exc_info.value.reason == "not_configured"
    assert exc_info.value.backend == "postgres"


def test_postgres_health_uses_connection_check(monkeypatch):
    monkeypatch.setenv("DATABASE_BACKEND", "postgres")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@postgres:5432/fundamentracker")

    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def execute(self, query, params):
            self.query = query
            self.params = params

        def fetchone(self):
            return (1,)

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def cursor(self):
            return FakeCursor()

    monkeypatch.setattr(db, "_connect_postgres", lambda: FakeConnection())

    assert db.check_database_connectivity() == {"status": "ok", "backend": "postgres"}


def test_wait_for_database_ready_retries_postgres(monkeypatch):
    monkeypatch.setenv("DATABASE_BACKEND", "postgres")
    failures = [db.DatabaseHealthError("connection_failed", "not ready", backend="postgres")]

    def fake_check_database_connectivity():
        if failures:
            raise failures.pop()
        return {"status": "ok", "backend": "postgres"}

    monkeypatch.setattr(db, "check_database_connectivity", fake_check_database_connectivity)
    monkeypatch.setattr(db.time, "sleep", lambda _seconds: None)

    assert db.wait_for_database_ready(timeout_seconds=1, interval_seconds=0) == {
        "status": "ok",
        "backend": "postgres",
    }


def test_build_watchlist_serializes_alert_values():
    watchlist = db._build_watchlist(
        [{"symbol": "AAPL", "name": "Apple Inc."}],
        [
            {
                "id": "alert-id",
                "ticker_symbol": "AAPL",
                "metric": "pe",
                "operator": "<",
                "target_value": "20.5",
                "is_active": True,
                "is_triggered": False,
                "reference_value": None,
                "alert_type": "absolute",
                "current_value": "21.7",
            }
        ],
    )

    assert watchlist["AAPL"]["alerts"] == [
        {
            "id": "alert-id",
            "metric": "pe",
            "operator": "<",
            "target": 20.5,
            "is_active": True,
            "is_triggered": False,
            "reference_value": None,
            "alert_type": "absolute",
            "current_value": 21.7,
        }
    ]
