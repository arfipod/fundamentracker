from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

import pytest

from db import postgres_to_sqlite as migration


def test_adapt_value_preserves_portable_types():
    now = datetime(2026, 9, 13, 12, 30, tzinfo=timezone.utc)
    identifier = UUID("00000000-0000-0000-0000-000000000001")

    assert migration.adapt_value("alerts", "is_active", True) == 1
    assert migration.adapt_value("alerts", "current_stale", False) == 0
    assert migration.adapt_value("alerts", "target_value", Decimal("12.5")) == 12.5
    assert migration.adapt_value("alerts", "created_at", now) == now.isoformat()
    assert migration.adapt_value("tags", "id", identifier) == str(identifier)
    assert json.loads(
        migration.adapt_value("signals", "raw_payload", {"nested": [1, 2]})
    ) == {"nested": [1, 2]}


def _sample_rows():
    now = datetime(2026, 9, 13, 12, 30, tzinfo=timezone.utc)
    today = date(2026, 9, 13)
    ticker = "AAPL"
    tag_id = UUID("00000000-0000-0000-0000-000000000001")
    alert_id = UUID("00000000-0000-0000-0000-000000000002")
    history_id = UUID("00000000-0000-0000-0000-000000000003")
    signal_id = UUID("00000000-0000-0000-0000-000000000004")
    provider_id = UUID("00000000-0000-0000-0000-000000000005")
    snapshot_id = UUID("00000000-0000-0000-0000-000000000006")

    return {
        "tickers": [{
            "symbol": ticker,
            "name": "Apple Inc.",
            "status": "watching",
            "priority": "high",
            "notes": None,
            "thesis": "fixture",
            "target_action": None,
            "updated_at": now,
            "created_at": now,
        }],
        "tags": [{"id": tag_id, "name": "Quality", "color": "#00aa88", "created_at": now}],
        "ticker_tags": [{"ticker_symbol": ticker, "tag_id": tag_id}],
        "alerts": [{
            "id": alert_id,
            "ticker_symbol": ticker,
            "metric": "pe",
            "operator": "<",
            "target_value": Decimal("25.0"),
            "is_active": True,
            "is_triggered": False,
            "reference_value": None,
            "alert_type": "absolute",
            "current_value": Decimal("26.5"),
            "current_source": "fixture",
            "current_as_of_date": today,
            "current_fetched_at": now,
            "current_expires_at": now,
            "current_stale": False,
            "current_confidence": Decimal("0.9"),
            "deleted_at": None,
            "restored_at": None,
            "created_at": now,
        }],
        "alert_history": [{
            "id": history_id,
            "alert_id": alert_id,
            "triggered_at": now,
            "trigger_value": Decimal("24.0"),
            "target_value": Decimal("25.0"),
            "ticker_symbol": ticker,
            "company_name": "Apple Inc.",
            "metric": "pe",
            "operator": "<",
            "alert_type": "absolute",
            "reference_value": None,
            "current_value": Decimal("24.0"),
            "source": "fixture",
            "as_of_date": today,
            "fetched_at": now,
            "message": "fixture",
        }],
        "signals": [{
            "id": signal_id,
            "ticker_symbol": ticker,
            "company_name": "Apple Inc.",
            "signal_type": "alert_triggered",
            "severity": "info",
            "title": "Fixture signal",
            "message": "fixture",
            "metric": "pe",
            "current_value": Decimal("24.0"),
            "previous_value": None,
            "target_value": Decimal("25.0"),
            "source": "fixture",
            "as_of_date": today,
            "fetched_at": now,
            "created_at": now,
            "acknowledged_at": None,
            "dismissed_at": None,
            "raw_payload": {"alert_id": str(alert_id)},
        }],
        "scan_settings": [{"id": 1, "interval_seconds": 3600, "last_scan_time": 123456}],
        "data_providers": [{
            "id": provider_id,
            "name": "yfinance",
            "provider_type": "market_data",
            "is_enabled": True,
            "priority": 100,
            "config": {"fixture": True},
            "created_at": now,
            "updated_at": now,
        }],
        "metric_snapshots": [{
            "id": snapshot_id,
            "symbol": ticker,
            "metric": "pe",
            "value": Decimal("26.5"),
            "unit": "ratio",
            "currency": "USD",
            "source": "fixture",
            "as_of_date": today,
            "fetched_at": now,
            "expires_at": now,
            "confidence": Decimal("0.9"),
            "raw_payload": {"fixture": True},
        }],
        "provider_health": [{
            "provider": "yfinance",
            "status": "ok",
            "last_ok_at": now,
            "last_error_at": None,
            "last_error": None,
        }],
    }


def test_migration_copies_and_verifies_consistent_snapshot(monkeypatch, tmp_path):
    rows = _sample_rows()

    class FakeSource:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def execute(self, statement):
            assert "REPEATABLE READ READ ONLY" in statement

        def rollback(self):
            return None

    class FakePsycopg:
        @staticmethod
        def connect(database_url, row_factory=None):
            assert database_url == "postgresql://fixture"
            return FakeSource()

    monkeypatch.setattr(migration, "_postgres_driver", lambda: (FakePsycopg, object()))
    monkeypatch.setattr(
        migration,
        "_source_count",
        lambda _source, table: len(rows[table]),
    )
    monkeypatch.setattr(
        migration,
        "_stream_source_rows",
        lambda _source, _dict_row, spec, _batch_size: iter(rows[spec.name]),
    )

    destination = tmp_path / "fundamentracker.db"
    counts = migration.migrate_postgres_to_sqlite(
        "postgresql://fixture",
        destination,
        batch_size=2,
    )

    assert counts == {spec.name: len(rows[spec.name]) for spec in migration.TABLES}
    with sqlite3.connect(destination) as conn:
        conn.row_factory = sqlite3.Row
        assert conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0] == 1
        signal = dict(conn.execute("SELECT * FROM signals").fetchone())
        provider = dict(conn.execute("SELECT * FROM data_providers").fetchone())
        assert json.loads(signal["raw_payload"])["alert_id"].endswith("0002")
        assert json.loads(provider["config"]) == {"fixture": True}
        assert conn.execute("SELECT interval_seconds FROM scan_settings WHERE id=1").fetchone()[0] == 3600
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []


def test_migration_refuses_existing_target_without_explicit_replace(tmp_path):
    destination = tmp_path / "fundamentracker.db"
    destination.write_bytes(b"do-not-touch")

    with pytest.raises(FileExistsError):
        migration.migrate_postgres_to_sqlite("postgresql://unused", destination)

    assert destination.read_bytes() == b"do-not-touch"
