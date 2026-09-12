from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from repositories.base import DatabaseHealthError
from repositories.sqlite import SQLiteRepository


@pytest.fixture
def repository(tmp_path):
    return SQLiteRepository(database_path=str(tmp_path / "fundamentracker.db"))


def test_sqlite_requires_configured_path(monkeypatch):
    monkeypatch.delenv("SQLITE_PATH", raising=False)
    repository = SQLiteRepository()

    assert repository.is_configured() is False
    with pytest.raises(DatabaseHealthError) as exc_info:
        repository.check_connectivity()

    assert exc_info.value.reason == "not_configured"
    assert exc_info.value.backend == "sqlite"


def test_sqlite_initializes_schema_and_wal(repository):
    assert repository.check_connectivity() == {"status": "ok", "backend": "sqlite"}

    database_path = repository._get_database_path()
    assert database_path is not None
    with sqlite3.connect(database_path) as conn:
        journal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        foreign_keys = repository._connect().execute("PRAGMA foreign_keys").fetchone()[0]
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }

    assert journal_mode == "wal"
    assert foreign_keys == 1
    assert {"tickers", "alerts", "signals", "metric_snapshots", "provider_health"} <= tables


def test_sqlite_watchlist_tags_and_ticker_metadata(repository):
    created = repository.add_ticker_db("AAPL", "Apple Inc.")
    assert created[0]["symbol"] == "AAPL"

    updated = repository.update_ticker_metadata(
        "AAPL",
        {"status": "owned", "priority": "high", "thesis": "Durable ecosystem"},
    )
    assert updated["status"] == "owned"
    assert updated["priority"] == "high"

    tag = repository.add_tag_to_ticker("AAPL", "Quality", "#00aa88")
    assert tag["name"] == "Quality"

    watchlist = repository.get_watchlist()
    assert watchlist["AAPL"]["name"] == "Apple Inc."
    assert watchlist["AAPL"]["status"] == "owned"
    assert watchlist["AAPL"]["tags"] == [
        {"id": tag["id"], "name": "Quality", "color": "#00aa88"}
    ]

    assert repository.remove_tag_from_ticker("AAPL", "quality") is True
    assert repository.get_watchlist()["AAPL"]["tags"] == []


def test_sqlite_alert_lifecycle_and_history(repository):
    repository.add_ticker_db("MSFT", "Microsoft")
    alert = repository.add_alert_db("MSFT", "pe", "<", 25.0)[0]
    alert_id = alert["id"]

    assert alert["is_active"] is True
    assert alert["is_triggered"] is False

    toggled = repository.toggle_alert_active(alert_id, False)[0]
    assert toggled["is_active"] is False

    now = datetime.now(timezone.utc)
    updated = repository.update_alert_status(
        alert_id,
        True,
        23.5,
        {
            "source": "fixture",
            "as_of_date": now.date(),
            "fetched_at": now,
            "expires_at": now + timedelta(hours=1),
            "stale": False,
            "confidence": 0.95,
        },
    )[0]
    assert updated["is_triggered"] is True
    assert updated["current_value"] == 23.5
    assert updated["current_stale"] is False

    history = repository.log_alert_history(
        alert_id,
        23.5,
        25.0,
        {"source": "fixture", "message": "threshold crossed"},
    )
    assert history[0]["ticker_symbol"] == "MSFT"
    assert history[0]["company_name"] == "Microsoft"

    fetched_history = repository.get_alert_history_db()
    assert fetched_history[0]["alerts"] == {"ticker_symbol": "MSFT", "metric": "pe"}

    assert repository.delete_alert_db(alert_id=alert_id) is True
    assert repository.get_alerts() == []
    assert repository.get_deleted_alerts_db()[0]["id"] == alert_id

    restored = repository.restore_alert_db(alert_id)[0]
    assert restored["deleted_at"] is None
    assert restored["restored_at"] is not None


def test_sqlite_metric_snapshots_round_trip_json(repository):
    now = datetime.now(timezone.utc)
    snapshot = repository.save_metric_snapshot(
        {
            "symbol": "aapl",
            "metric": "pe",
            "value": 22.75,
            "unit": "ratio",
            "currency": "USD",
            "source": "fixture",
            "as_of_date": now.date(),
            "fetched_at": now,
            "expires_at": now + timedelta(hours=1),
            "confidence": 0.9,
            "raw_payload": {"provider": "fixture", "nested": {"ok": True}},
        }
    )

    assert snapshot is not None
    assert snapshot["symbol"] == "AAPL"
    assert snapshot["metric"] == "pe"
    assert snapshot["raw_payload"]["nested"] == {"ok": True}

    fresh = repository.get_fresh_metric_snapshot("AAPL", "PE", now)
    assert fresh is not None
    assert fresh["value"] == 22.75
    assert fresh["raw_payload"]["provider"] == "fixture"


def test_sqlite_provider_health_preserves_existing_optional_values(repository):
    now = datetime.now(timezone.utc)
    first = repository.upsert_provider_health(
        "yfinance",
        "ok",
        last_ok_at=now,
    )
    assert first is not None

    second = repository.upsert_provider_health(
        "yfinance",
        "degraded",
        last_error="temporary failure",
    )
    assert second is not None
    assert second["status"] == "degraded"
    assert second["last_ok_at"] == now.isoformat()
    assert second["last_error"] == "temporary failure"


def test_sqlite_signals_and_scan_settings(repository):
    signal = repository.create_signal(
        {
            "ticker_symbol": "NVDA",
            "signal_type": "alert_triggered",
            "title": "Threshold crossed",
            "raw_payload": {"alert_id": "abc"},
        }
    )
    assert signal is not None
    assert signal["severity"] == "info"
    assert signal["raw_payload"] == {"alert_id": "abc"}
    assert repository.get_signals(status="open")[0]["id"] == signal["id"]

    acknowledged = repository.acknowledge_signal(signal["id"])
    assert acknowledged is not None
    assert acknowledged["acknowledged_at"] is not None
    assert repository.get_signals(status="open") == []

    assert repository.get_scan_settings_db()["interval_seconds"] == 0
    settings = repository.update_scan_settings_db(interval=3600, last_scan_time=12345)
    assert settings == {"id": 1, "interval_seconds": 3600, "last_scan_time": 12345}


def test_sqlite_cascades_ticker_deletion(repository):
    repository.add_ticker_db("GOOG", "Alphabet")
    repository.add_alert_db("GOOG", "pe", "<", 20)
    repository.add_tag_to_ticker("GOOG", "Platform")

    assert repository.delete_ticker_db("GOOG") is True
    assert repository.get_tickers() == []
    assert repository.get_alerts() == []
