from __future__ import annotations

import os
import time
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

import requests

DEFAULT_TIMEOUT_SECONDS = 5
DEFAULT_POSTGRES_STARTUP_TIMEOUT_SECONDS = 60
SUPPORTED_DATABASE_BACKENDS = {"supabase_rest", "postgres"}


class DatabaseHealthError(Exception):
    def __init__(self, reason: str, detail: str, backend: str | None = None):
        self.reason = reason
        self.detail = detail
        self.backend = backend or get_database_backend()
        super().__init__(detail)


def get_database_backend() -> str:
    backend = os.getenv("DATABASE_BACKEND", "supabase_rest").strip().lower()
    aliases = {
        "supabase": "supabase_rest",
        "postgresql": "postgres",
    }
    return aliases.get(backend, backend)


def is_postgres_backend() -> bool:
    return get_database_backend() == "postgres"


def _get_supabase_config() -> tuple[str | None, str | None]:
    return os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY")


def _get_supabase_headers() -> dict[str, str]:
    _, supabase_key = _get_supabase_config()
    return {
        "apikey": supabase_key or "",
        "Authorization": f"Bearer {supabase_key or ''}",
        "Content-Type": "application/json",
    }


def is_database_configured() -> bool:
    backend = get_database_backend()
    if backend == "postgres":
        return bool(os.getenv("DATABASE_URL"))
    if backend == "supabase_rest":
        supabase_url, supabase_key = _get_supabase_config()
        return bool(supabase_url and supabase_key)
    return False


def check_database_connectivity() -> dict[str, str]:
    backend = get_database_backend()
    if backend == "postgres":
        return _check_postgres_connectivity()
    if backend == "supabase_rest":
        return _check_supabase_connectivity()

    raise DatabaseHealthError(
        reason="unsupported_backend",
        detail="DATABASE_BACKEND must be either 'supabase_rest' or 'postgres'.",
        backend=backend,
    )


def wait_for_database_ready(
    timeout_seconds: int = DEFAULT_POSTGRES_STARTUP_TIMEOUT_SECONDS,
    interval_seconds: float = 2.0,
) -> dict[str, str]:
    if not is_postgres_backend():
        return check_database_connectivity()

    deadline = time.monotonic() + timeout_seconds
    last_error: DatabaseHealthError | None = None

    while time.monotonic() < deadline:
        try:
            return check_database_connectivity()
        except DatabaseHealthError as error:
            last_error = error
            time.sleep(interval_seconds)

    detail = "PostgreSQL did not become ready before startup timed out."
    reason = "timeout"
    if last_error is not None:
        detail = f"{detail} Last error: {last_error.detail}"
        reason = last_error.reason

    raise DatabaseHealthError(reason=reason, detail=detail, backend="postgres")


def _check_supabase_connectivity() -> dict[str, str]:
    supabase_url, supabase_key = _get_supabase_config()
    if not supabase_url or not supabase_key:
        raise DatabaseHealthError(
            reason="not_configured",
            detail="SUPABASE_URL and SUPABASE_KEY must be configured.",
            backend="supabase_rest",
        )

    url = f"{supabase_url}/rest/v1/scan_settings"
    params = {"select": "id", "id": "eq.1", "limit": "1"}

    try:
        response = requests.get(
            url,
            headers=_get_supabase_headers(),
            params=params,
            timeout=DEFAULT_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.exceptions.Timeout as exc:
        raise DatabaseHealthError(
            reason="timeout",
            detail="Database readiness check timed out.",
            backend="supabase_rest",
        ) from exc
    except requests.exceptions.RequestException as exc:
        status_code = exc.response.status_code if exc.response is not None else None
        detail = "Database readiness check failed."
        if status_code is not None:
            detail = f"{detail} Upstream status: {status_code}."
        raise DatabaseHealthError(
            reason="connection_failed",
            detail=detail,
            backend="supabase_rest",
        ) from exc

    return {
        "status": "ok",
        "backend": "supabase_rest",
    }


def _check_postgres_connectivity() -> dict[str, str]:
    if not os.getenv("DATABASE_URL"):
        raise DatabaseHealthError(
            reason="not_configured",
            detail="DATABASE_URL must be configured when DATABASE_BACKEND=postgres.",
            backend="postgres",
        )

    try:
        with _connect_postgres() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM scan_settings WHERE id = %s LIMIT 1", (1,))
                cur.fetchone()
    except DatabaseHealthError:
        raise
    except Exception as exc:
        raise DatabaseHealthError(
            reason="connection_failed",
            detail="PostgreSQL readiness check failed.",
            backend="postgres",
        ) from exc

    return {
        "status": "ok",
        "backend": "postgres",
    }


def _import_psycopg():
    try:
        import psycopg
    except ImportError as exc:
        raise DatabaseHealthError(
            reason="driver_missing",
            detail="The psycopg package is required when DATABASE_BACKEND=postgres.",
            backend="postgres",
        ) from exc
    return psycopg


def _dict_row_factory():
    try:
        from psycopg.rows import dict_row
    except ImportError as exc:
        raise DatabaseHealthError(
            reason="driver_missing",
            detail="The psycopg package is required when DATABASE_BACKEND=postgres.",
            backend="postgres",
        ) from exc
    return dict_row


def _connect_postgres(row_factory=None):
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise DatabaseHealthError(
            reason="not_configured",
            detail="DATABASE_URL must be configured when DATABASE_BACKEND=postgres.",
            backend="postgres",
        )

    psycopg = _import_psycopg()
    kwargs: dict[str, Any] = {"connect_timeout": DEFAULT_TIMEOUT_SECONDS}
    if row_factory is not None:
        kwargs["row_factory"] = row_factory
    return psycopg.connect(database_url, **kwargs)


def _serialize_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    return value


def _serialize_row(row: dict[str, Any]) -> dict[str, Any]:
    return {key: _serialize_value(value) for key, value in row.items()}


def _postgres_query_all(query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    dict_row = _dict_row_factory()
    with _connect_postgres(row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return [_serialize_row(row) for row in cur.fetchall()]


def _postgres_execute(query: str, params: tuple[Any, ...] = ()) -> bool:
    with _connect_postgres() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.rowcount > 0


def _supabase_req(method: str, endpoint: str, **kwargs):
    supabase_url, supabase_key = _get_supabase_config()
    if not supabase_url or not supabase_key:
        return [] if method == "GET" else None

    url = f"{supabase_url}/rest/v1/{endpoint}"
    headers = _get_supabase_headers()
    if "headers" in kwargs:
        headers.update(kwargs.pop("headers"))

    kwargs.setdefault("timeout", DEFAULT_TIMEOUT_SECONDS)

    try:
        response = requests.request(method, url, headers=headers, **kwargs)
        response.raise_for_status()
        if method != "DELETE":
            if response.text.strip() == "":
                return []
            return response.json()
        return True
    except requests.exceptions.RequestException as e:
        print(f"DB Error: {method} {url} - {e}")
        if hasattr(e, "response") and e.response is not None:
            print("Details:", e.response.text)
        return [] if method == "GET" else None


def _to_float(value: Any, default: float | None = None) -> float | None:
    if value is None:
        return default
    return float(value)


def _build_watchlist(tickers: list[dict[str, Any]], alerts: list[dict[str, Any]]) -> dict[str, Any]:
    watchlist: dict[str, Any] = {}
    for ticker in tickers:
        symbol = ticker.get("symbol")
        if not symbol:
            continue
        watchlist[symbol] = {
            "name": ticker.get("name") or symbol,
            "alerts": [],
        }

    for alert in alerts:
        symbol = alert.get("ticker_symbol")
        if symbol not in watchlist:
            continue

        watchlist[symbol]["alerts"].append(
            {
                "id": str(alert.get("id")),
                "metric": alert.get("metric"),
                "operator": alert.get("operator"),
                "target": _to_float(alert.get("target_value"), 0),
                "is_active": alert.get("is_active", True),
                "is_triggered": alert.get("is_triggered", False),
                "reference_value": _to_float(alert.get("reference_value")),
                "alert_type": alert.get("alert_type") or "absolute",
                "current_value": _to_float(alert.get("current_value")),
            }
        )

    return watchlist


def get_watchlist():
    if is_postgres_backend():
        tickers = _postgres_query_all(
            "SELECT symbol, name, created_at FROM tickers ORDER BY symbol"
        )
        alerts = _postgres_query_all(
            """
            SELECT id, ticker_symbol, metric, operator, target_value, is_active,
                   is_triggered, reference_value, alert_type, current_value, created_at
            FROM alerts
            ORDER BY created_at ASC
            """
        )
        return _build_watchlist(tickers, alerts)

    tickers = _supabase_req("GET", "tickers") or []
    alerts = _supabase_req("GET", "alerts") or []
    return _build_watchlist(tickers, alerts)


def get_alerts():
    if is_postgres_backend():
        return _postgres_query_all(
            """
            SELECT id, ticker_symbol, metric, operator, target_value, is_active,
                   is_triggered, reference_value, alert_type, current_value, created_at
            FROM alerts
            ORDER BY created_at ASC
            """
        )
    return _supabase_req("GET", "alerts") or []


def get_tickers():
    if is_postgres_backend():
        return _postgres_query_all("SELECT symbol, name, created_at FROM tickers ORDER BY symbol")
    return _supabase_req("GET", "tickers") or []


def add_ticker_db(symbol, company_name):
    if is_postgres_backend():
        return _postgres_query_all(
            """
            INSERT INTO tickers (symbol, name)
            VALUES (%s, %s)
            ON CONFLICT (symbol) DO UPDATE SET name = EXCLUDED.name
            RETURNING symbol, name, created_at
            """,
            (symbol, company_name),
        )

    headers = {"Prefer": "resolution=merge-duplicates, return=representation"}
    payload = {"symbol": symbol, "name": company_name}
    return _supabase_req("POST", "tickers", json=payload, headers=headers)


def add_alert_db(symbol, metric, operator, target_value, alert_type="absolute", reference_value=None):
    if is_postgres_backend():
        return _postgres_query_all(
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

    payload = {
        "ticker_symbol": symbol,
        "metric": metric,
        "operator": operator,
        "target_value": target_value,
        "alert_type": alert_type,
        "reference_value": reference_value,
        "is_active": True,
        "is_triggered": False,
    }
    headers = {"Prefer": "return=representation"}
    return _supabase_req("POST", "alerts", json=payload, headers=headers)


def update_alert_target(alert_id, new_target):
    if is_postgres_backend():
        return _postgres_query_all(
            """
            UPDATE alerts
            SET target_value = %s
            WHERE id = %s
            RETURNING id, ticker_symbol, metric, operator, target_value, is_active,
                      is_triggered, reference_value, alert_type, current_value, created_at
            """,
            (float(new_target), alert_id),
        )

    payload = {"target_value": float(new_target)}
    headers = {"Prefer": "return=representation"}
    return _supabase_req("PATCH", f"alerts?id=eq.{alert_id}", json=payload, headers=headers)


def toggle_alert_active(alert_id, is_active):
    if is_postgres_backend():
        return _postgres_query_all(
            """
            UPDATE alerts
            SET is_active = %s
            WHERE id = %s
            RETURNING id, ticker_symbol, metric, operator, target_value, is_active,
                      is_triggered, reference_value, alert_type, current_value, created_at
            """,
            (is_active, alert_id),
        )

    payload = {"is_active": is_active}
    headers = {"Prefer": "return=representation"}
    return _supabase_req("PATCH", f"alerts?id=eq.{alert_id}", json=payload, headers=headers)


def update_alert_status(alert_id, is_triggered, current_value=None):
    if is_postgres_backend():
        if current_value is None:
            return _postgres_query_all(
                """
                UPDATE alerts
                SET is_triggered = %s
                WHERE id = %s
                RETURNING id, ticker_symbol, metric, operator, target_value, is_active,
                          is_triggered, reference_value, alert_type, current_value, created_at
                """,
                (is_triggered, alert_id),
            )

        return _postgres_query_all(
            """
            UPDATE alerts
            SET is_triggered = %s, current_value = %s
            WHERE id = %s
            RETURNING id, ticker_symbol, metric, operator, target_value, is_active,
                      is_triggered, reference_value, alert_type, current_value, created_at
            """,
            (is_triggered, float(current_value), alert_id),
        )

    payload = {"is_triggered": is_triggered}
    if current_value is not None:
        payload["current_value"] = float(current_value)
    headers = {"Prefer": "return=representation"}
    return _supabase_req("PATCH", f"alerts?id=eq.{alert_id}", json=payload, headers=headers)


def delete_alert_db(alert_id=None, symbol=None, metric=None):
    if is_postgres_backend():
        if alert_id:
            return _postgres_execute("DELETE FROM alerts WHERE id = %s", (alert_id,))
        if symbol and metric:
            return _postgres_execute(
                "DELETE FROM alerts WHERE ticker_symbol = %s AND metric = %s",
                (symbol, metric),
            )
        return False

    if alert_id:
        return _supabase_req("DELETE", f"alerts?id=eq.{alert_id}")
    if symbol and metric:
        return _supabase_req("DELETE", f"alerts?ticker_symbol=eq.{symbol}&metric=eq.{metric}")
    return False


def delete_ticker_db(symbol):
    if is_postgres_backend():
        return _postgres_execute("DELETE FROM tickers WHERE symbol = %s", (symbol,))
    return _supabase_req("DELETE", f"tickers?symbol=eq.{symbol}")


def _ensure_scan_settings_postgres() -> dict[str, Any]:
    dict_row = _dict_row_factory()
    with _connect_postgres(row_factory=dict_row) as conn:
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
            return _serialize_row(row) if row else {"interval_seconds": 0, "last_scan_time": 0}


def get_scan_settings_db():
    if is_postgres_backend():
        return _ensure_scan_settings_postgres()

    res = _supabase_req("GET", "scan_settings?id=eq.1")
    if res and len(res) > 0:
        return res[0]
    return {"interval_seconds": 0, "last_scan_time": 0}


def update_scan_settings_db(interval=None, last_scan_time=None):
    if is_postgres_backend():
        _ensure_scan_settings_postgres()

        assignments: list[str] = []
        params: list[Any] = []
        if interval is not None:
            assignments.append("interval_seconds = %s")
            params.append(interval)
        if last_scan_time is not None:
            assignments.append("last_scan_time = %s")
            params.append(last_scan_time)

        if not assignments:
            return get_scan_settings_db()

        params.append(1)
        rows = _postgres_query_all(
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

    payload = {}
    if interval is not None:
        payload["interval_seconds"] = interval
    if last_scan_time is not None:
        payload["last_scan_time"] = last_scan_time

    headers = {"Prefer": "return=representation"}
    res = _supabase_req("PATCH", "scan_settings?id=eq.1", json=payload, headers=headers)
    if res and len(res) > 0:
        return res[0]
    return {}


def log_alert_history(alert_id, trigger_val, target_val):
    if is_postgres_backend():
        return _postgres_query_all(
            """
            INSERT INTO alert_history (alert_id, trigger_value, target_value)
            VALUES (%s, %s, %s)
            RETURNING id, alert_id, triggered_at, trigger_value, target_value
            """,
            (alert_id, trigger_val, target_val),
        )

    payload = {
        "alert_id": alert_id,
        "trigger_value": trigger_val,
        "target_value": target_val,
    }
    headers = {"Prefer": "return=representation"}
    return _supabase_req("POST", "alert_history", json=payload, headers=headers)


def get_alert_history_db(limit=50):
    if is_postgres_backend():
        rows = _postgres_query_all(
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

    return (
        _supabase_req(
            "GET",
            f"alert_history?select=*,alerts(ticker_symbol,metric)&order=triggered_at.desc&limit={limit}",
        )
        or []
    )
