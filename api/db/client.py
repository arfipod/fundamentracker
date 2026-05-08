from __future__ import annotations

import time
from datetime import datetime
from typing import Any

from repositories.base import (
    DEFAULT_POSTGRES_STARTUP_TIMEOUT_SECONDS,
    DEFAULT_TIMEOUT_SECONDS,
    METRIC_SNAPSHOT_COLUMNS,
    PROVIDER_HEALTH_COLUMNS,
    SUPPORTED_DATABASE_BACKENDS,
    DatabaseHealthError,
    build_watchlist as _build_watchlist,
    serialize_row as _serialize_row,
    serialize_value as _serialize_value,
    to_float as _to_float,
)
from repositories import factory as repository_factory


def get_database_backend() -> str:
    return repository_factory.get_database_backend()


def is_postgres_backend() -> bool:
    return repository_factory.is_postgres_backend()


def is_database_configured() -> bool:
    return repository_factory.is_database_configured()


def check_database_connectivity() -> dict[str, str]:
    return repository_factory.check_database_connectivity()


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


def _repository():
    return repository_factory.get_repository()


def get_watchlist():
    return _repository().get_watchlist()


def get_alerts():
    return _repository().get_alerts()


def get_fresh_metric_snapshot(symbol: str, metric: str, now: datetime) -> dict[str, Any] | None:
    return _repository().get_fresh_metric_snapshot(symbol, metric, now)


def get_latest_metric_snapshot(symbol: str, metric: str) -> dict[str, Any] | None:
    return _repository().get_latest_metric_snapshot(symbol, metric)


def save_metric_snapshot(snapshot: dict[str, Any]) -> dict[str, Any] | None:
    return _repository().save_metric_snapshot(snapshot)


def upsert_provider_health(
    provider: str,
    status: str,
    *,
    last_ok_at: datetime | None = None,
    last_error_at: datetime | None = None,
    last_error: str | None = None,
) -> dict[str, Any] | None:
    return _repository().upsert_provider_health(
        provider,
        status,
        last_ok_at=last_ok_at,
        last_error_at=last_error_at,
        last_error=last_error,
    )


def get_provider_health() -> list[dict[str, Any]]:
    return _repository().get_provider_health()


def get_tickers():
    return _repository().get_tickers()


def get_tags():
    return _repository().get_tags()


def add_ticker_db(symbol, company_name):
    return _repository().add_ticker_db(symbol, company_name)


def update_ticker_metadata(symbol, metadata):
    return _repository().update_ticker_metadata(symbol, metadata)


def add_tag_to_ticker(symbol, name, color=None):
    return _repository().add_tag_to_ticker(symbol, name, color)


def remove_tag_from_ticker(symbol, tag_name_or_id):
    return _repository().remove_tag_from_ticker(symbol, tag_name_or_id)


def add_alert_db(
    symbol,
    metric,
    operator,
    target_value,
    alert_type="absolute",
    reference_value=None,
):
    return _repository().add_alert_db(
        symbol,
        metric,
        operator,
        target_value,
        alert_type,
        reference_value,
    )


def update_alert_target(alert_id, new_target):
    return _repository().update_alert_target(alert_id, new_target)


def toggle_alert_active(alert_id, is_active):
    return _repository().toggle_alert_active(alert_id, is_active)


def restore_alert_db(alert_id):
    return _repository().restore_alert_db(alert_id)


def get_deleted_alerts_db():
    return _repository().get_deleted_alerts_db()


def update_alert_status(alert_id, is_triggered, current_value=None, current_metadata=None):
    return _repository().update_alert_status(alert_id, is_triggered, current_value, current_metadata)


def delete_alert_db(alert_id=None, symbol=None, metric=None):
    return _repository().delete_alert_db(alert_id=alert_id, symbol=symbol, metric=metric)


def delete_ticker_db(symbol):
    return _repository().delete_ticker_db(symbol)


def get_scan_settings_db():
    return _repository().get_scan_settings_db()


def update_scan_settings_db(interval=None, last_scan_time=None):
    return _repository().update_scan_settings_db(
        interval=interval,
        last_scan_time=last_scan_time,
    )


def log_alert_history(alert_id, trigger_val, target_val, metadata=None):
    return _repository().log_alert_history(alert_id, trigger_val, target_val, metadata)


def get_alert_history_db(limit=50):
    return _repository().get_alert_history_db(limit=limit)
