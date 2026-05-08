from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

from repositories.base import (
    DEFAULT_TIMEOUT_SECONDS,
    METRIC_SNAPSHOT_COLUMNS,
    PROVIDER_HEALTH_COLUMNS,
    DatabaseHealthError,
    build_watchlist,
    serialize_row,
    serialize_value,
)


class PostgresRepository:
    DatabaseHealthError = DatabaseHealthError
    backend = "postgres"
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

    def __init__(
        self,
        *,
        database_url: str | None = None,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    ):
        self.database_url = database_url
        self.timeout_seconds = timeout_seconds

    def _get_database_url(self) -> str | None:
        return self.database_url or os.getenv("DATABASE_URL")

    def is_configured(self) -> bool:
        return bool(self._get_database_url())

    def _import_psycopg(self):
        try:
            import psycopg
        except ImportError as exc:
            raise DatabaseHealthError(
                reason="driver_missing",
                detail="The psycopg package is required when DATABASE_BACKEND=postgres.",
                backend=self.backend,
            ) from exc
        return psycopg

    def _dict_row_factory(self):
        try:
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise DatabaseHealthError(
                reason="driver_missing",
                detail="The psycopg package is required when DATABASE_BACKEND=postgres.",
                backend=self.backend,
            ) from exc
        return dict_row

    def _connect(self, row_factory=None):
        database_url = self._get_database_url()
        if not database_url:
            raise DatabaseHealthError(
                reason="not_configured",
                detail="DATABASE_URL must be configured when DATABASE_BACKEND=postgres.",
                backend=self.backend,
            )

        psycopg = self._import_psycopg()
        kwargs: dict[str, Any] = {"connect_timeout": self.timeout_seconds}
        if row_factory is not None:
            kwargs["row_factory"] = row_factory
        return psycopg.connect(database_url, **kwargs)

    @staticmethod
    def _jsonb_param(value: Any) -> str | None:
        if value is None:
            return None
        return json.dumps(value, default=str)

    def _query_all(self, query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        dict_row = self._dict_row_factory()
        with self._connect(row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                return [serialize_row(row) for row in cur.fetchall()]

    def _execute(self, query: str, params: tuple[Any, ...] = ()) -> bool:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                return cur.rowcount > 0

    def check_connectivity(self) -> dict[str, str]:
        if not self._get_database_url():
            raise DatabaseHealthError(
                reason="not_configured",
                detail="DATABASE_URL must be configured when DATABASE_BACKEND=postgres.",
                backend=self.backend,
            )

        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1 FROM scan_settings WHERE id = %s LIMIT 1", (1,))
                    cur.fetchone()
        except DatabaseHealthError:
            raise
        except Exception as exc:
            raise DatabaseHealthError(
                reason="connection_failed",
                detail="PostgreSQL readiness check failed.",
                backend=self.backend,
            ) from exc

        return {
            "status": "ok",
            "backend": self.backend,
        }

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
        symbol = symbol.upper()
        metric = metric.lower()

        rows = self._query_all(
            f"""
            SELECT {METRIC_SNAPSHOT_COLUMNS}
            FROM metric_snapshots
            WHERE symbol = %s
              AND metric = %s
              AND expires_at > %s
            ORDER BY fetched_at DESC
            LIMIT 1
            """,
            (symbol, metric, now),
        )
        return rows[0] if rows else None

    def get_latest_metric_snapshot(self, symbol: str, metric: str) -> dict[str, Any] | None:
        symbol = symbol.upper()
        metric = metric.lower()

        rows = self._query_all(
            f"""
            SELECT {METRIC_SNAPSHOT_COLUMNS}
            FROM metric_snapshots
            WHERE symbol = %s
              AND metric = %s
            ORDER BY fetched_at DESC
            LIMIT 1
            """,
            (symbol, metric),
        )
        return rows[0] if rows else None

    def save_metric_snapshot(self, snapshot: dict[str, Any]) -> dict[str, Any] | None:
        payload = {
            "symbol": snapshot.get("symbol", "").upper(),
            "metric": snapshot.get("metric", "").lower(),
            "value": snapshot.get("value"),
            "unit": snapshot.get("unit"),
            "currency": snapshot.get("currency"),
            "source": snapshot.get("source"),
            "as_of_date": serialize_value(snapshot.get("as_of_date")),
            "fetched_at": serialize_value(snapshot.get("fetched_at")),
            "expires_at": serialize_value(snapshot.get("expires_at")),
            "confidence": snapshot.get("confidence"),
            "raw_payload": snapshot.get("raw_payload"),
        }

        rows = self._query_all(
            """
            INSERT INTO metric_snapshots (
                symbol, metric, value, unit, currency, source, as_of_date,
                fetched_at, expires_at, confidence, raw_payload
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
            RETURNING id, symbol, metric, value, unit, currency, source,
                      as_of_date, fetched_at, expires_at, confidence, raw_payload
            """,
            (
                payload["symbol"],
                payload["metric"],
                payload["value"],
                payload["unit"],
                payload["currency"],
                payload["source"],
                payload["as_of_date"],
                payload["fetched_at"],
                payload["expires_at"],
                payload["confidence"],
                self._jsonb_param(payload["raw_payload"]),
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
        payload = {
            "provider": provider,
            "status": status,
            "last_ok_at": serialize_value(last_ok_at),
            "last_error_at": serialize_value(last_error_at),
            "last_error": last_error,
        }

        rows = self._query_all(
            """
            INSERT INTO provider_health (
                provider, status, last_ok_at, last_error_at, last_error
            )
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (provider) DO UPDATE SET
                status = EXCLUDED.status,
                last_ok_at = COALESCE(EXCLUDED.last_ok_at, provider_health.last_ok_at),
                last_error_at = COALESCE(EXCLUDED.last_error_at, provider_health.last_error_at),
                last_error = COALESCE(EXCLUDED.last_error, provider_health.last_error)
            RETURNING provider, status, last_ok_at, last_error_at, last_error
            """,
            (
                payload["provider"],
                payload["status"],
                payload["last_ok_at"],
                payload["last_error_at"],
                payload["last_error"],
            ),
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
            VALUES (%s, %s)
            ON CONFLICT (symbol) DO UPDATE SET
                name = EXCLUDED.name,
                updated_at = NOW()
            RETURNING symbol, name, status, priority, notes, thesis,
                      target_action, created_at, updated_at
            """,
            (symbol, company_name),
        )

    def update_ticker_metadata(self, symbol, metadata):
        allowed_columns = ("status", "priority", "notes", "thesis", "target_action")
        assignments = []
        params = []
        for column in allowed_columns:
            if column in metadata:
                assignments.append(f"{column} = %s")
                params.append(metadata[column])

        if not assignments:
            rows = self._query_all(
                f"SELECT {self.TICKER_COLUMNS} FROM tickers WHERE symbol = %s",
                (symbol,),
            )
            return rows[0] if rows else None

        assignments.append("updated_at = NOW()")
        params.append(symbol)
        rows = self._query_all(
            f"""
            UPDATE tickers
            SET {', '.join(assignments)}
            WHERE symbol = %s
            RETURNING symbol, name, status, priority, notes, thesis,
                      target_action, created_at, updated_at
            """,
            tuple(params),
        )
        return rows[0] if rows else None

    def add_tag_to_ticker(self, symbol, name, color=None):
        rows = self._query_all(
            """
            WITH tag_row AS (
                INSERT INTO tags (name, color)
                VALUES (%s, %s)
                ON CONFLICT (name) DO UPDATE SET
                    color = COALESCE(EXCLUDED.color, tags.color)
                RETURNING id, name, color
            ), linked AS (
                INSERT INTO ticker_tags (ticker_symbol, tag_id)
                SELECT %s, id
                FROM tag_row
                ON CONFLICT (ticker_symbol, tag_id) DO NOTHING
                RETURNING tag_id
            )
            SELECT id, name, color
            FROM tag_row
            """,
            (name, color, symbol),
        )
        return rows[0] if rows else None

    def remove_tag_from_ticker(self, symbol, tag_name_or_id):
        return self._execute(
            """
            DELETE FROM ticker_tags tt
            USING tags t
            WHERE tt.tag_id = t.id
              AND tt.ticker_symbol = %s
              AND (t.id::text = %s OR lower(t.name) = lower(%s))
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
        return self._query_all(
            """
            INSERT INTO alerts (
                ticker_symbol, metric, operator, target_value, alert_type,
                reference_value, is_active, is_triggered
            )
            VALUES (%s, %s, %s, %s, %s, %s, TRUE, FALSE)
            RETURNING id, ticker_symbol, metric, operator, target_value, is_active,
                      is_triggered, reference_value, alert_type, current_value,
                      current_source, current_as_of_date, current_fetched_at,
                      current_expires_at, current_stale, current_confidence,
                      deleted_at, restored_at, created_at
            """,
            (symbol, metric, operator, target_value, alert_type, reference_value),
        )

    def update_alert_target(self, alert_id, new_target):
        return self._query_all(
            """
            UPDATE alerts
            SET target_value = %s
            WHERE id = %s
              AND deleted_at IS NULL
            RETURNING id, ticker_symbol, metric, operator, target_value, is_active,
                      is_triggered, reference_value, alert_type, current_value,
                      current_source, current_as_of_date, current_fetched_at,
                      current_expires_at, current_stale, current_confidence,
                      deleted_at, restored_at, created_at
            """,
            (float(new_target), alert_id),
        )

    def toggle_alert_active(self, alert_id, is_active):
        return self._query_all(
            """
            UPDATE alerts
            SET is_active = %s
            WHERE id = %s
              AND deleted_at IS NULL
            RETURNING id, ticker_symbol, metric, operator, target_value, is_active,
                      is_triggered, reference_value, alert_type, current_value,
                      current_source, current_as_of_date, current_fetched_at,
                      current_expires_at, current_stale, current_confidence,
                      deleted_at, restored_at, created_at
            """,
            (is_active, alert_id),
        )

    def restore_alert_db(self, alert_id):
        return self._query_all(
            """
            UPDATE alerts
            SET deleted_at = NULL, restored_at = NOW()
            WHERE id = %s
            RETURNING id, ticker_symbol, metric, operator, target_value, is_active,
                      is_triggered, reference_value, alert_type, current_value,
                      current_source, current_as_of_date, current_fetched_at,
                      current_expires_at, current_stale, current_confidence,
                      deleted_at, restored_at, created_at
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
                """
                UPDATE alerts
                SET is_triggered = %s
                WHERE id = %s
                  AND deleted_at IS NULL
                RETURNING id, ticker_symbol, metric, operator, target_value, is_active,
                          is_triggered, reference_value, alert_type, current_value,
                          current_source, current_as_of_date, current_fetched_at,
                          current_expires_at, current_stale, current_confidence,
                          deleted_at, restored_at, created_at
                """,
                (is_triggered, alert_id),
            )

        return self._query_all(
            """
            UPDATE alerts
            SET is_triggered = %s,
                current_value = %s,
                current_source = %s,
                current_as_of_date = %s,
                current_fetched_at = %s,
                current_expires_at = %s,
                current_stale = %s,
                current_confidence = %s
            WHERE id = %s
              AND deleted_at IS NULL
            RETURNING id, ticker_symbol, metric, operator, target_value, is_active,
                      is_triggered, reference_value, alert_type, current_value,
                      current_source, current_as_of_date, current_fetched_at,
                      current_expires_at, current_stale, current_confidence,
                      deleted_at, restored_at, created_at
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
        if alert_id:
            return self._execute(
                """
                UPDATE alerts
                SET deleted_at = COALESCE(deleted_at, NOW())
                WHERE id = %s
                """,
                (alert_id,),
            )
        if symbol and metric:
            return self._execute(
                """
                UPDATE alerts
                SET deleted_at = COALESCE(deleted_at, NOW())
                WHERE ticker_symbol = %s
                  AND metric = %s
                  AND deleted_at IS NULL
                """,
                (symbol, metric),
            )
        return False

    def delete_ticker_db(self, symbol):
        return self._execute("DELETE FROM tickers WHERE symbol = %s", (symbol,))

    def _ensure_scan_settings(self) -> dict[str, Any]:
        dict_row = self._dict_row_factory()
        with self._connect(row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO scan_settings (id, interval_seconds, last_scan_time)
                    VALUES (1, 0, 0)
                    ON CONFLICT (id) DO NOTHING
                    """
                )
                cur.execute(
                    """
                    SELECT id, interval_seconds, last_scan_time
                    FROM scan_settings
                    WHERE id = %s
                    """,
                    (1,),
                )
                row = cur.fetchone()
                return serialize_row(row) if row else {"interval_seconds": 0, "last_scan_time": 0}

    def get_scan_settings_db(self):
        return self._ensure_scan_settings()

    def update_scan_settings_db(self, interval=None, last_scan_time=None):
        self._ensure_scan_settings()

        assignments: list[str] = []
        params: list[Any] = []
        if interval is not None:
            assignments.append("interval_seconds = %s")
            params.append(interval)
        if last_scan_time is not None:
            assignments.append("last_scan_time = %s")
            params.append(last_scan_time)

        if not assignments:
            return self.get_scan_settings_db()

        params.append(1)
        rows = self._query_all(
            f"""
            UPDATE scan_settings
            SET {', '.join(assignments)}
            WHERE id = %s
            RETURNING id, interval_seconds, last_scan_time
            """,
            tuple(params),
        )
        if rows:
            return rows[0]
        return {}

    def log_alert_history(self, alert_id, trigger_val, target_val, metadata=None):
        metadata = metadata or {}
        return self._query_all(
            """
            INSERT INTO alert_history (
                alert_id, trigger_value, target_value, ticker_symbol, company_name,
                metric, operator, alert_type, reference_value, current_value,
                source, as_of_date, fetched_at, message
            )
            SELECT
                a.id, %s, %s,
                COALESCE(%s, a.ticker_symbol),
                COALESCE(%s, t.name),
                COALESCE(%s, a.metric),
                COALESCE(%s, a.operator),
                COALESCE(%s, a.alert_type),
                COALESCE(%s, a.reference_value),
                COALESCE(%s, %s),
                %s, %s, %s, %s
            FROM alerts a
            LEFT JOIN tickers t ON t.symbol = a.ticker_symbol
            WHERE a.id = %s
            RETURNING id, alert_id, triggered_at, trigger_value, target_value,
                      ticker_symbol, company_name, metric, operator, alert_type,
                      reference_value, current_value, source, as_of_date, fetched_at, message
            """,
            (
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
            LIMIT %s
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
        rows = self._query_all(
            """
            INSERT INTO signals (
                ticker_symbol, company_name, signal_type, severity, title, message,
                metric, current_value, previous_value, target_value, source,
                as_of_date, fetched_at, raw_payload
            )
            VALUES (
                %s, %s, %s, COALESCE(%s, 'info'), %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s::jsonb
            )
            RETURNING id, ticker_symbol, company_name, signal_type, severity, title,
                      message, metric, current_value, previous_value, target_value,
                      source, as_of_date, fetched_at, created_at, acknowledged_at,
                      dismissed_at, raw_payload
            """,
            (
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
                self._jsonb_param(payload.get("raw_payload")),
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
            LIMIT %s
            """,
            (limit,),
        )

    def acknowledge_signal(self, signal_id):
        rows = self._query_all(
            f"""
            UPDATE signals
            SET acknowledged_at = COALESCE(acknowledged_at, NOW())
            WHERE id = %s
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
            SET dismissed_at = COALESCE(dismissed_at, NOW())
            WHERE id = %s
            RETURNING {self.SIGNAL_COLUMNS}
            """,
            (signal_id,),
        )
        return rows[0] if rows else None
