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
        tickers = self._query_all("SELECT symbol, name, created_at FROM tickers ORDER BY symbol")
        alerts = self._query_all(
            """
            SELECT id, ticker_symbol, metric, operator, target_value, is_active,
                   is_triggered, reference_value, alert_type, current_value, created_at
            FROM alerts
            ORDER BY created_at ASC
            """
        )
        return build_watchlist(tickers, alerts)

    def get_alerts(self):
        return self._query_all(
            """
            SELECT id, ticker_symbol, metric, operator, target_value, is_active,
                   is_triggered, reference_value, alert_type, current_value, created_at
            FROM alerts
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
        return self._query_all("SELECT symbol, name, created_at FROM tickers ORDER BY symbol")

    def add_ticker_db(self, symbol, company_name):
        return self._query_all(
            """
            INSERT INTO tickers (symbol, name)
            VALUES (%s, %s)
            ON CONFLICT (symbol) DO UPDATE SET name = EXCLUDED.name
            RETURNING symbol, name, created_at
            """,
            (symbol, company_name),
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
                      is_triggered, reference_value, alert_type, current_value, created_at
            """,
            (symbol, metric, operator, target_value, alert_type, reference_value),
        )

    def update_alert_target(self, alert_id, new_target):
        return self._query_all(
            """
            UPDATE alerts
            SET target_value = %s
            WHERE id = %s
            RETURNING id, ticker_symbol, metric, operator, target_value, is_active,
                      is_triggered, reference_value, alert_type, current_value, created_at
            """,
            (float(new_target), alert_id),
        )

    def toggle_alert_active(self, alert_id, is_active):
        return self._query_all(
            """
            UPDATE alerts
            SET is_active = %s
            WHERE id = %s
            RETURNING id, ticker_symbol, metric, operator, target_value, is_active,
                      is_triggered, reference_value, alert_type, current_value, created_at
            """,
            (is_active, alert_id),
        )

    def update_alert_status(self, alert_id, is_triggered, current_value=None):
        if current_value is None:
            return self._query_all(
                """
                UPDATE alerts
                SET is_triggered = %s
                WHERE id = %s
                RETURNING id, ticker_symbol, metric, operator, target_value, is_active,
                          is_triggered, reference_value, alert_type, current_value, created_at
                """,
                (is_triggered, alert_id),
            )

        return self._query_all(
            """
            UPDATE alerts
            SET is_triggered = %s, current_value = %s
            WHERE id = %s
            RETURNING id, ticker_symbol, metric, operator, target_value, is_active,
                      is_triggered, reference_value, alert_type, current_value, created_at
            """,
            (is_triggered, float(current_value), alert_id),
        )

    def delete_alert_db(self, alert_id=None, symbol=None, metric=None):
        if alert_id:
            return self._execute("DELETE FROM alerts WHERE id = %s", (alert_id,))
        if symbol and metric:
            return self._execute(
                "DELETE FROM alerts WHERE ticker_symbol = %s AND metric = %s",
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

    def log_alert_history(self, alert_id, trigger_val, target_val):
        return self._query_all(
            """
            INSERT INTO alert_history (alert_id, trigger_value, target_value)
            VALUES (%s, %s, %s)
            RETURNING id, alert_id, triggered_at, trigger_value, target_value
            """,
            (alert_id, trigger_val, target_val),
        )

    def get_alert_history_db(self, limit=50):
        rows = self._query_all(
            """
            SELECT h.id, h.alert_id, h.triggered_at, h.trigger_value, h.target_value,
                   a.ticker_symbol AS alert_ticker_symbol,
                   a.metric AS alert_metric
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
