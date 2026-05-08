from __future__ import annotations

import os
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Protocol
from uuid import UUID

DEFAULT_TIMEOUT_SECONDS = 5
DEFAULT_POSTGRES_STARTUP_TIMEOUT_SECONDS = 60
SUPPORTED_DATABASE_BACKENDS = {"supabase_rest", "postgres"}
METRIC_SNAPSHOT_COLUMNS = (
    "id,symbol,metric,value,unit,currency,source,as_of_date,"
    "fetched_at,expires_at,confidence,raw_payload"
)
PROVIDER_HEALTH_COLUMNS = "provider,status,last_ok_at,last_error_at,last_error"


def normalize_database_backend(backend: str | None) -> str:
    raw_backend = "supabase_rest" if backend is None else backend
    normalized = raw_backend.strip().lower()
    aliases = {
        "supabase": "supabase_rest",
        "postgresql": "postgres",
    }
    return aliases.get(normalized, normalized)


class DatabaseHealthError(Exception):
    def __init__(self, reason: str, detail: str, backend: str | None = None):
        self.reason = reason
        self.detail = detail
        self.backend = backend or normalize_database_backend(os.getenv("DATABASE_BACKEND"))
        super().__init__(detail)


class TickerRepository(Protocol):
    def get_tickers(self) -> list[dict[str, Any]]:
        ...

    def get_tags(self) -> list[dict[str, Any]]:
        ...

    def add_ticker_db(self, symbol: str, company_name: str) -> Any:
        ...

    def update_ticker_metadata(
        self,
        symbol: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any] | None:
        ...

    def add_tag_to_ticker(
        self,
        symbol: str,
        name: str,
        color: str | None = None,
    ) -> dict[str, Any] | None:
        ...

    def remove_tag_from_ticker(self, symbol: str, tag_name_or_id: str) -> bool:
        ...

    def delete_ticker_db(self, symbol: str) -> Any:
        ...


class AlertRepository(Protocol):
    def get_watchlist(self) -> dict[str, Any]:
        ...

    def get_alerts(self) -> list[dict[str, Any]]:
        ...

    def add_alert_db(
        self,
        symbol: str,
        metric: str,
        operator: str,
        target_value: float,
        alert_type: str = "absolute",
        reference_value: float | None = None,
    ) -> Any:
        ...

    def update_alert_target(self, alert_id: str, new_target: float) -> Any:
        ...

    def toggle_alert_active(self, alert_id: str, is_active: bool) -> Any:
        ...

    def restore_alert_db(self, alert_id: str) -> Any:
        ...

    def get_deleted_alerts_db(self) -> list[dict[str, Any]]:
        ...

    def update_alert_status(
        self,
        alert_id: str,
        is_triggered: bool,
        current_value: float | None = None,
    ) -> Any:
        ...

    def delete_alert_db(
        self,
        alert_id: str | None = None,
        symbol: str | None = None,
        metric: str | None = None,
    ) -> Any:
        ...


class AlertHistoryRepository(Protocol):
    def log_alert_history(
        self,
        alert_id: str,
        trigger_val: float,
        target_val: float,
        metadata: dict[str, Any] | None = None,
    ) -> Any:
        ...

    def get_alert_history_db(self, limit: int = 50) -> list[dict[str, Any]]:
        ...


class ScanSettingsRepository(Protocol):
    def get_scan_settings_db(self) -> dict[str, Any]:
        ...

    def update_scan_settings_db(
        self,
        interval: int | None = None,
        last_scan_time: int | None = None,
    ) -> dict[str, Any]:
        ...


class MetricSnapshotRepository(Protocol):
    def get_fresh_metric_snapshot(
        self,
        symbol: str,
        metric: str,
        now: datetime,
    ) -> dict[str, Any] | None:
        ...

    def get_latest_metric_snapshot(self, symbol: str, metric: str) -> dict[str, Any] | None:
        ...

    def save_metric_snapshot(self, snapshot: dict[str, Any]) -> dict[str, Any] | None:
        ...


class ProviderHealthRepository(Protocol):
    def upsert_provider_health(
        self,
        provider: str,
        status: str,
        *,
        last_ok_at: datetime | None = None,
        last_error_at: datetime | None = None,
        last_error: str | None = None,
    ) -> dict[str, Any] | None:
        ...

    def get_provider_health(self) -> list[dict[str, Any]]:
        ...


class FundamenTrackerRepository(
    TickerRepository,
    AlertRepository,
    AlertHistoryRepository,
    ScanSettingsRepository,
    MetricSnapshotRepository,
    ProviderHealthRepository,
    Protocol,
):
    DatabaseHealthError: type[DatabaseHealthError]

    def is_configured(self) -> bool:
        ...

    def check_connectivity(self) -> dict[str, str]:
        ...

    def check_database_connectivity(self) -> dict[str, str]:
        ...


def serialize_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    return value


def serialize_row(row: dict[str, Any]) -> dict[str, Any]:
    return {key: serialize_value(value) for key, value in row.items()}


def to_float(value: Any, default: float | None = None) -> float | None:
    if value is None:
        return default
    return float(value)


def _normalize_tag_row(row: dict[str, Any]) -> dict[str, Any] | None:
    tag = row.get("tags") if isinstance(row.get("tags"), dict) else row
    tag_id = tag.get("tag_id") or tag.get("id")
    name = tag.get("tag_name") or tag.get("name")
    if not tag_id or not name:
        return None
    return {
        "id": str(tag_id),
        "name": name,
        "color": tag.get("tag_color") or tag.get("color"),
    }


def build_watchlist(
    tickers: list[dict[str, Any]],
    alerts: list[dict[str, Any]],
    ticker_tags: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    watchlist: dict[str, Any] = {}
    for ticker in tickers:
        symbol = ticker.get("symbol")
        if not symbol:
            continue
        watchlist[symbol] = {
            "name": ticker.get("name") or symbol,
            "status": ticker.get("status") or "watching",
            "priority": ticker.get("priority") or "medium",
            "notes": ticker.get("notes"),
            "thesis": ticker.get("thesis"),
            "target_action": ticker.get("target_action"),
            "tags": [],
            "alerts": [],
        }

    for row in ticker_tags or []:
        symbol = row.get("ticker_symbol")
        if symbol not in watchlist:
            continue
        tag = _normalize_tag_row(row)
        if tag is not None:
            watchlist[symbol]["tags"].append(tag)

    for alert in alerts:
        symbol = alert.get("ticker_symbol")
        if symbol not in watchlist:
            continue

        watchlist[symbol]["alerts"].append(
            {
                "id": str(alert.get("id")),
                "metric": alert.get("metric"),
                "operator": alert.get("operator"),
                "target": to_float(alert.get("target_value"), 0),
                "is_active": alert.get("is_active", True),
                "is_triggered": alert.get("is_triggered", False),
                "reference_value": to_float(alert.get("reference_value")),
                "alert_type": alert.get("alert_type") or "absolute",
                "current_value": to_float(alert.get("current_value")),
            }
        )

    return watchlist
