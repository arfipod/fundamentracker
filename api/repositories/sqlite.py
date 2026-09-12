from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import date, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from repositories.base import (
    DEFAULT_TIMEOUT_SECONDS,
    METRIC_SNAPSHOT_COLUMNS,
    PROVIDER_HEALTH_COLUMNS,
    DatabaseHealthError,
    build_watchlist,
    serialize_value,
)


class SQLiteRepository:
    DatabaseHealthError = DatabaseHealthError
    backend = "sqlite"
    ALERT_COLUMNS = (
        "id, ticker_symbol, metric, operator, target_value, is_active, "
        "is_triggered, reference_value, alert_type, current_value, "
        "current_source, current_as_of_date, current_fetched_at, "
        "current_expires_at, current_stale, current_confidence, "
        "deleted_at, restored_at, created_at"
    )
    TICKER_COLUMNS = (
        "symbol, name, status, priority, notes, thesis, target_action, "
        "created_at, updated_at"
    )
    SIGNAL_COLUMNS = (
        "id, ticker_symbol, company_name, signal_type, severity, title, message, "
        "metric, current_value, previous_value, target_value, source, as_of_date, "
        "fetched_at, created_at, acknowledged_at, dismissed_at, raw_payload"
    )
    BOOLEAN_COLUMNS = {"is_active", "is_triggered", "current_stale", "is_enabled"}
    JSON_COLUMNS = {"raw_payload", "config"}

    def __init__(
        self,
        *,
        database_path: str | None = None,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        schema_path: str | None = None,
    ):
        self.database_path = database_path
        self.timeout_seconds = timeout_seconds
        self.schema_path = schema_path
        self._schema_lock = threading.Lock()
        self._schema_ready = False

    def _get_database_path(self) -> str | None:
        return self.database_path or os.getenv("SQLITE_PATH")

    def _get_schema_path(self) -> Path:
        if self.schema_path:
            return Path(self.schema_path)
        return Path(__file__).resolve().parents[2] / "db" / "sqlite" / "001_schema.sql"

    def is_configured(self) -> bool:
        return bool(self._get_database_path())

    def _open_connection(self) -> sqlite3.Connection:
        database_path = self._get_database_path()
        if not database_path:
            raise DatabaseHealthError(
                reason="not_configured",
                detail="SQLITE_PATH must be configured when DATABASE_BACKEND=sqlite.",
                backend=self.backend,
            )

        try:
            if database_path != ":memory:":
                Path(database_path).expanduser().parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(database_path, timeout=self.timeout_seconds)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute(f"PRAGMA busy_timeout = {max(1, int(self.timeout_seconds * 1000))}")
            return conn
        except (OSError, sqlite3.Error) as exc:
            raise DatabaseHealthError(
                reason="connection_failed",
                detail="SQLite connection failed.",
                backend=self.backend,
            ) from exc

    def _ensure_schema(self) -> None:
        if self._schema_ready:
            return
        with self._schema_lock:
            if self._schema_ready:
                return

            schema_path = self._get_schema_path()
            try:
                schema_sql = schema_path.read_text(encoding="utf-8")
            except OSError as exc:
                raise DatabaseHealthError(
                    reason="schema_missing",
                    detail=f"SQLite schema could not be read from {schema_path}.",
                    backend=self.backend,
                ) from exc

            try:
                with self._open_connection() as conn:
                    conn.execute("PRAGMA journal_mode = WAL")
                    conn.execute("PRAGMA synchronous = NORMAL")
                    conn.executescript(schema_sql)
            except DatabaseHealthError:
                raise
            except sqlite3.Error as exc:
                raise DatabaseHealthError(
                    reason="schema_failed",
                    detail="SQLite schema initialization failed.",
                    backend=self.backend,
                ) from exc
            self._schema_ready = True

    def _connect(self) -> sqlite3.Connection:
        self._ensure_schema()
        return self._open_connection()

    @staticmethod
    def _adapt_param(value: Any) -> Any:
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, (dict, list)):
            return json.dumps(value, default=str, separators=(",", ":"))
        return value

    @classmethod
    def _normalize_row(cls, row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
        data = dict(row)
        for column in cls.BOOLEAN_COLUMNS:
            if column in data and data[column] is not None:
                data[column] = bool(data[column])
        for column in cls.JSON_COLUMNS:
            value = data.get(column)
            if isinstance(value, str):
                try:
                    data[column] = json.loads(value)
                except json.JSONDecodeError:
                    pass
        return {key: serialize_value(value) for key, value in data.items()}

    def _query_all(self, query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        adapted = tuple(self._adapt_param(value) for value in params)
        try:
            with self._connect() as conn:
                cursor = conn.execute(query, adapted)
                return [self._normalize_row(row) for row in cursor.fetchall()]
        except DatabaseHealthError:
            raise
        except sqlite3.Error as exc:
            raise DatabaseHealthError(
                reason="query_failed",
                detail="SQLite query failed.",
                backend=self.backend,
            ) from exc

    def _execute(self, query: str, params: tuple[Any, ...] = ()) -> bool:
        adapted = tuple(self._adapt_param(value) for value in params)
        try:
            with self._connect() as conn:
                cursor = conn.execute(query, adapted)
                return cursor.rowcount > 0
        except DatabaseHealthError:
            raise
        except sqlite3.Error as exc:
            raise DatabaseHealthError(
                reason="query_failed",
                detail="SQLite write failed.",
                backend=self.backend,
            ) from exc

    def check_connectivity(self) -> dict[str, str]:
        if not self._get_database_path():
            raise DatabaseHealthError(
                reason="not_configured",
                detail="SQLITE_PATH must be configured when DATABASE_BACKEND=sqlite.",
                backend=self.backend,
            )
        try:
            with self._connect() as conn:
                conn.execute("SELECT 1 FROM scan_settings WHERE id = ? LIMIT 1", (1,)).fetchone()
        except DatabaseHealthError:
            raise
        except sqlite3.Error as exc:
            raise DatabaseHealthError(
                reason="connection_failed",
                detail="SQLite readiness check failed.",
                backend=self.backend,
            ) from exc
        return {"status": "ok", "backend": self.backend}

    def check_database_connectivity(self) -> dict[str, str]:
        return self.check_connectivity()

    def get_watchlist(self):
        tickers = self._query_all(f"SELECT {self.TICKER_COLUMNS} FROM tickers ORDER BY symbol")
        alerts = self._query_all(
            f"""
            SELECT {self.ALERT_COLUMNS}
            FROM alerts
            WHERE deleted_at IS NULL
            ORDER BY created_at ASC
            """
        )
        ticker_tags = self._query_all(
            """
            SELECT tt.ticker_symbol, t.id AS tag_id, t.name AS tag_name, t.color AS tag_color
            FROM ticker_tags tt
            JOIN tags t ON t.id = tt.tag_id
            ORDER BY lower(t.name) ASC
            """
        )
        return build_watchlist(tickers, alerts, ticker_tags)

    def get_alerts(self):
        return self._query_all(
            f"""
            SELECT {self.ALERT_COLUMNS}
            FROM alerts
            WHERE deleted_at IS NULL
            ORDER BY created_at ASC
            """
        )

    def get_fresh_metric_snapshot(
        self,
        symbol: str,
        metric: str,
        now: datetime,
    ) -> dict[str, Any] | None:
        rows = self._query_all(
            f"""
            SELECT {METRIC_SNAPSHOT_COLUMNS}
            FROM metric_snapshots
            WHERE symbol = ?
              AND metric = ?
              AND expires_at > ?
            ORDER BY fetched_at DESC
            LIMIT 1
            """,
            (symbol.upper(), metric.lower(), now),
        )
        return rows[0] if rows else None

    def get_latest_metric_snapshot(self, symbol: str, metric: str) -> dict[str, Any] | None:
        rows = self._query_all(
            f"""
            SELECT {METRIC_SNAPSHOT_COLUMNS}
            FROM metric_snapshots
            WHERE symbol = ?
              AND metric = ?
            ORDER BY fetched_at DESC
            LIMIT 1
            """,
            (symbol.upper(), metric.lower()),
        )
        return rows[0] if rows else None

    def save_metric_snapshot(self, snapshot: dict[str, Any]) -> dict[str, Any] | None:
        snapshot_id = str(uuid4())
        rows = self._query_all(
            """
            INSERT INTO metric_snapshots (
                id, symbol, metric, value, unit, currency, source, as_of_date,
                fetched_at, expires_at, confidence, raw_payload
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING id, symbol, metric, value, unit, currency, source,
                      as_of_date, fetched_at, expires_at, confidence, raw_payload
            """,
            (
                snapshot_id,
                snapshot.get("symbol", "").upper(),
                snapshot.get("metric", "").lower(),
                snapshot.get("value"),
                snapshot.get("unit"),
                snapshot.get("currency"),
                snapshot.get("source"),
                snapshot.get("as_of_date"),
                snapshot.get("fetched_at"),
                snapshot.get("expires_at"),
                snapshot.get("confidence"),
                snapshot.get("raw_payload"),
            ),
        )
        return rows[0] if rows else None

    def upsert_provider_health(
        self,
        provider: str,
        status: str,
        *,
        last_ok_at: datetime | None = None,
        last_error_at: datetime | None = None,
        last_error: str | None = None,
    ) -> dict[str, Any] | None:
        rows = self._query_all(
            """
            INSERT INTO provider_health (
                provider, status, last_ok_at, last_error_at, last_error
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (provider) DO UPDATE SET
                status = excluded.status,
                last_ok_at = COALESCE(excluded.last_ok_at, provider_health.last_ok_at),
                last_error_at = COALESCE(excluded.last_error_at, provider_health.last_error_at),
                last_error = COALESCE(excluded.last_error, provider_health.last_error)
            RETURNING provider, status, last_ok_at, last_error_at, last_error
            """,
            (provider, status, last_ok_at, last_error_at, last_error),
        )
        return rows[0] if rows else None

    def get_provider_health(self) -> list[dict[str, Any]]:
        return self._query_all(
            f"""
            SELECT {PROVIDER_HEALTH_COLUMNS}
            FROM provider_health
            ORDER BY provider ASC
            """
        )

    def get_tickers(self):
        return self._query_all(f"SELECT {self.TICKER_COLUMNS} FROM tickers ORDER BY symbol")

    def get_tags(self):
        return self._query_all("SELECT id, name, color, created_at FROM tags ORDER BY lower(name)")

    def add_ticker_db(self, symbol, company_name):
        return self._query_all(
            """
            INSERT INTO tickers (symbol, name)
            VALUES (?, ?)
            ON CONFLICT (symbol) DO UPDATE SET
                name = excluded.name,
                updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
            RETURNING symbol, name, status, priority, notes, thesis,
                      target_action, created_at, updated_at
            """,
            (symbol, company_name),
        )

    def update_ticker_metadata(self, symbol, metadata):
        allowed_columns = ("status", "priority", "notes", "thesis", "target_action")
        assignments: list[str] = []
        params: list[Any] = []
        for column in allowed_columns:
            if column in metadata:
                assignments.append(f"{column} = ?")
                params.append(metadata[column])

        if not assignments:
            rows = self._query_all(
                f"SELECT {self.TICKER_COLUMNS} FROM tickers WHERE symbol = ?",
                (symbol,),
            )
            return rows[0] if rows else None

        assignments.append("updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')")
        params.append(symbol)
        rows = self._query_all(
            f"""
            UPDATE tickers
            SET {', '.join(assignments)}
            WHERE symbol = ?
            RETURNING symbol, name, status, priority, notes, thesis,
                      target_action, created_at, updated_at
            """,
            tuple(params),
        )
        return rows[0] if rows else None

    def add_tag_to_ticker(self, symbol, name, color=None):
        try:
            with self._connect() as conn:
                tag_id = str(uuid4())
                cursor = conn.execute(
                    """
                    INSERT INTO tags (id, name, color)
                    VALUES (?, ?, ?)
                    ON CONFLICT (name) DO UPDATE SET
                        color = COALESCE(excluded.color, tags.color)
                    RETURNING id, name, color
                    """,
                    (tag_id, name, color),
                )
                row = cursor.fetchone()
                if row is None:
                    return None
                tag = self._normalize_row(row)
                conn.execute(
                    """
                    INSERT INTO ticker_tags (ticker_symbol, tag_id)
                    VALUES (?, ?)
                    ON CONFLICT (ticker_symbol, tag_id) DO NOTHING
                    """,
                    (symbol, tag["id"]),
                )
                return tag
        except DatabaseHealthError:
            raise
        except sqlite3.Error as exc:
            raise DatabaseHealthError(
                reason="query_failed",
                detail="SQLite tag update failed.",
                backend=self.backend,
            ) from exc

    def remove_tag_from_ticker(self, symbol, tag_name_or_id):
        return self._execute(
            """
            DELETE FROM ticker_tags
            WHERE ticker_symbol = ?
              AND tag_id IN (
                  SELECT id
                  FROM tags
                  WHERE id = ? OR lower(name) = lower(?)
              )
            """,
            (symbol, tag_name_or_id, tag_name_or_id),
        )

    def add_alert_db(
        self,
        symbol,
        metric,
        operator,
        target_value,
        alert_type="absolute",
        reference_value=None,
    ):
        alert_id = str(uuid4())
        return self._query_all(
            """
            INSERT INTO alerts (
                id, ticker_symbol, metric, operator, target_value, alert_type,
                reference_value, is_active, is_triggered
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, 0)
            RETURNING id, ticker_symbol, metric, operator, target_value, is_active,
                      is_triggered, reference_value, alert_type, current_value,
                      current_source, current_as_of_date, current_fetched_at,
                      current_expires_at, current_stale, current_confidence,
                      deleted_at, restored_at, created_at
            """,
            (alert_id, symbol, metric, operator, target_value, alert_type, reference_value),
        )

    def update_alert_target(self, alert_id, new_target):
        return self._query_all(
            f"""
            UPDATE alerts
            SET target_value = ?
            WHERE id = ?
              AND deleted_at IS NULL
            RETURNING {self.ALERT_COLUMNS}
            """,
            (float(new_target), alert_id),
        )

    def toggle_alert_active(self, alert_id, is_active):
        return self._query_all(
            f"""
            UPDATE alerts
            SET is_active = ?
            WHERE id = ?
              AND deleted_at IS NULL
            RETURNING {self.ALERT_COLUMNS}
            """,
            (is_active, alert_id),
        )

    def restore_alert_db(self, alert_id):
        return self._query_all(
            f"""
            UPDATE alerts
            SET deleted_at = NULL,
                restored_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
            WHERE id = ?
            RETURNING {self.ALERT_COLUMNS}
            """,
            (alert_id,),
        )

    def get_deleted_alerts_db(self):
        return self._query_all(
            f"""
            SELECT {self.ALERT_COLUMNS}
            FROM alerts
            WHERE deleted_at IS NOT NULL
            ORDER BY deleted_at DESC
            """
        )

    def update_alert_status(self, alert_id, is_triggered, current_value=None, current_metadata=None):
        current_metadata = current_metadata or {}
        if current_value is None:
            return self._query_all(
                f"""
                UPDATE alerts
                SET is_triggered = ?
                WHERE id = ?
                  AND deleted_at IS NULL
                RETURNING {self.ALERT_COLUMNS}
                """,
                (is_triggered, alert_id),
            )

        return self._query_all(
            f"""
            UPDATE alerts
            SET is_triggered = ?,
                current_value = ?,
                current_source = ?,
                current_as_of_date = ?,
                current_fetched_at = ?,
                current_expires_at = ?,
                current_stale = ?,
                current_confidence = ?
            WHERE id = ?
              AND deleted_at IS NULL
            RETURNING {self.ALERT_COLUMNS}
            """,
            (
                is_triggered,
                float(current_value),
                current_metadata.get("source"),
                current_metadata.get("as_of_date"),
                current_metadata.get("fetched_at"),
                current_metadata.get("expires_at"),
                current_metadata.get("stale"),
                current_metadata.get("confidence"),
                alert_id,
            ),
        )

    def delete_alert_db(self, alert_id=None, symbol=None, metric=None):
        now_sql = "strftime('%Y-%m-%dT%H:%M:%fZ', 'now')"
        if alert_id:
            return self._execute(
                f"""
                UPDATE alerts
                SET deleted_at = COALESCE(deleted_at, {now_sql})
                WHERE id = ?
                """,
                (alert_id,),
            )
        if symbol and metric:
            return self._execute(
                f"""
                UPDATE alerts
                SET deleted_at = COALESCE(deleted_at, {now_sql})
                WHERE ticker_symbol = ?
                  AND metric = ?
                  AND deleted_at IS NULL
                """,
                (symbol, metric),
            )
        return False

    def delete_ticker_db(self, symbol):
        return self._execute("DELETE FROM tickers WHERE symbol = ?", (symbol,))

    def _ensure_scan_settings(self) -> dict[str, Any]:
        try:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO scan_settings (id, interval_seconds, last_scan_time)
                    VALUES (1, 0, 0)
                    ON CONFLICT (id) DO NOTHING
                    """
                )
                row = conn.execute(
                    """
                    SELECT id, interval_seconds, last_scan_time
                    FROM scan_settings
                    WHERE id = ?
                    """,
                    (1,),
                ).fetchone()
                return self._normalize_row(row) if row else {
                    "interval_seconds": 0,
                    "last_scan_time": 0,
                }
        except DatabaseHealthError:
            raise
        except sqlite3.Error as exc:
            raise DatabaseHealthError(
                reason="query_failed",
                detail="SQLite scan settings initialization failed.",
                backend=self.backend,
            ) from exc

    def get_scan_settings_db(self):
        return self._ensure_scan_settings()

    def update_scan_settings_db(self, interval=None, last_scan_time=None):
        self._ensure_scan_settings()

        assignments: list[str] = []
        params: list[Any] = []
        if interval is not None:
            assignments.append("interval_seconds = ?")
            params.append(interval)
        if last_scan_time is not None:
            assignments.append("last_scan_time = ?")
            params.append(last_scan_time)

        if not assignments:
            return self.get_scan_settings_db()

        params.append(1)
        rows = self._query_all(
            f"""
            UPDATE scan_settings
            SET {', '.join(assignments)}
            WHERE id = ?
            RETURNING id, interval_seconds, last_scan_time
            """,
            tuple(params),
        )
        return rows[0] if rows else {}

    def log_alert_history(self, alert_id, trigger_val, target_val, metadata=None):
        metadata = metadata or {}
        history_id = str(uuid4())
        return self._query_all(
            """
            INSERT INTO alert_history (
                id, alert_id, trigger_value, target_value, ticker_symbol, company_name,
                metric, operator, alert_type, reference_value, current_value,
                source, as_of_date, fetched_at, message
            )
            SELECT
                ?, a.id, ?, ?,
                COALESCE(?, a.ticker_symbol),
                COALESCE(?, t.name),
                COALESCE(?, a.metric),
                COALESCE(?, a.operator),
                COALESCE(?, a.alert_type),
                COALESCE(?, a.reference_value),
                COALESCE(?, ?),
                ?, ?, ?, ?
            FROM alerts a
            LEFT JOIN tickers t ON t.symbol = a.ticker_symbol
            WHERE a.id = ?
            RETURNING id, alert_id, triggered_at, trigger_value, target_value,
                      ticker_symbol, company_name, metric, operator, alert_type,
                      reference_value, current_value, source, as_of_date, fetched_at, message
            """,
            (
                history_id,
                trigger_val,
                target_val,
                metadata.get("ticker_symbol"),
                metadata.get("company_name"),
                metadata.get("metric"),
                metadata.get("operator"),
                metadata.get("alert_type"),
                metadata.get("reference_value"),
                metadata.get("current_value"),
                trigger_val,
                metadata.get("source"),
                metadata.get("as_of_date"),
                metadata.get("fetched_at"),
                metadata.get("message"),
                alert_id,
            ),
        )

    def get_alert_history_db(self, limit=50):
        rows = self._query_all(
            """
            SELECT h.id, h.alert_id, h.triggered_at, h.trigger_value, h.target_value,
                   h.ticker_symbol, h.company_name, h.metric, h.operator, h.alert_type,
                   h.reference_value, h.current_value, h.source, h.as_of_date,
                   h.fetched_at, h.message,
                   COALESCE(h.ticker_symbol, a.ticker_symbol) AS alert_ticker_symbol,
                   COALESCE(h.metric, a.metric) AS alert_metric
            FROM alert_history h
            LEFT JOIN alerts a ON a.id = h.alert_id
            ORDER BY h.triggered_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        history = []
        for row in rows:
            ticker_symbol = row.pop("alert_ticker_symbol", None)
            metric = row.pop("alert_metric", None)
            if ticker_symbol or metric:
                row["alerts"] = {
                    "ticker_symbol": ticker_symbol,
                    "metric": metric,
                }
            history.append(row)
        return history

    def create_signal(self, payload):
        signal_id = str(uuid4())
        rows = self._query_all(
            """
            INSERT INTO signals (
                id, ticker_symbol, company_name, signal_type, severity, title, message,
                metric, current_value, previous_value, target_value, source,
                as_of_date, fetched_at, raw_payload
            )
            VALUES (?, ?, ?, ?, COALESCE(?, 'info'), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING id, ticker_symbol, company_name, signal_type, severity, title,
                      message, metric, current_value, previous_value, target_value,
                      source, as_of_date, fetched_at, created_at, acknowledged_at,
                      dismissed_at, raw_payload
            """,
            (
                signal_id,
                payload.get("ticker_symbol"),
                payload.get("company_name"),
                payload.get("signal_type"),
                payload.get("severity"),
                payload.get("title"),
                payload.get("message"),
                payload.get("metric"),
                payload.get("current_value"),
                payload.get("previous_value"),
                payload.get("target_value"),
                payload.get("source"),
                payload.get("as_of_date"),
                payload.get("fetched_at"),
                payload.get("raw_payload"),
            ),
        )
        return rows[0] if rows else None

    def get_signals(self, status="open", limit=50):
        where_clause = ""
        if status == "open":
            where_clause = "WHERE acknowledged_at IS NULL AND dismissed_at IS NULL"
        return self._query_all(
            f"""
            SELECT {self.SIGNAL_COLUMNS}
            FROM signals
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        )

    def acknowledge_signal(self, signal_id):
        rows = self._query_all(
            f"""
            UPDATE signals
            SET acknowledged_at = COALESCE(
                acknowledged_at,
                strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
            )
            WHERE id = ?
              AND dismissed_at IS NULL
            RETURNING {self.SIGNAL_COLUMNS}
            """,
            (signal_id,),
        )
        return rows[0] if rows else None

    def dismiss_signal(self, signal_id):
        rows = self._query_all(
            f"""
            UPDATE signals
            SET dismissed_at = COALESCE(
                dismissed_at,
                strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
            )
            WHERE id = ?
            RETURNING {self.SIGNAL_COLUMNS}
            """,
            (signal_id,),
        )
        return rows[0] if rows else None
