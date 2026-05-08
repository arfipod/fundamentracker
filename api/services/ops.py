from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable


def _epoch_to_iso(value: Any) -> str | None:
    if value in (None, "", 0):
        return None
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc).isoformat()
    except (TypeError, ValueError, OSError):
        return None


def _safe_provider_health(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    safe_rows: list[dict[str, Any]] = []
    for row in rows:
        safe_rows.append(
            {
                "provider": row.get("provider"),
                "status": row.get("status"),
                "last_ok_at": row.get("last_ok_at"),
                "last_error_at": row.get("last_error_at"),
                "has_error": bool(row.get("last_error")),
            }
        )
    return safe_rows


def _provider_status(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "unknown"
    statuses = {str(row.get("status", "")).lower() for row in rows}
    if statuses <= {"ok"}:
        return "ok"
    if "ok" in statuses:
        return "degraded"
    return "error"


def status_payload(
    *,
    db_client: Any,
    market_data_service: Any,
    service_name: str,
    service_version: str | None,
    timestamp_fn: Callable[[], str],
) -> dict[str, Any]:
    current_time = timestamp_fn()
    overall_status = "ok"

    payload: dict[str, Any] = {
        "status": overall_status,
        "api": {
            "status": "ok",
            "service": service_name,
        },
        "database": {
            "status": "unknown",
            "ready": False,
        },
        "provider_health": {
            "status": "unknown",
            "providers": [],
        },
        "scan": {
            "interval_seconds": None,
            "last_scan_time": None,
            "last_scan_at": None,
        },
        "server_time": current_time,
    }
    if service_version:
        payload["api"]["version"] = service_version

    try:
        database = db_client.check_database_connectivity()
        payload["database"] = {
            **database,
            "ready": database.get("status") == "ok",
        }
        if database.get("status") != "ok":
            overall_status = "degraded"
    except db_client.DatabaseHealthError as error:
        overall_status = "degraded"
        payload["database"] = {
            "status": "error",
            "ready": False,
            "backend": error.backend,
            "reason": error.reason,
            "detail": error.detail,
        }

    try:
        provider_rows = market_data_service.get_provider_health()
        providers = _safe_provider_health(provider_rows)
        provider_status = _provider_status(providers)
        payload["provider_health"] = {
            "status": provider_status,
            "providers": providers,
        }
        if provider_status in {"degraded", "error"}:
            overall_status = "degraded"
    except Exception:
        overall_status = "degraded"
        payload["provider_health"] = {
            "status": "unavailable",
            "providers": [],
        }

    try:
        scan_settings = db_client.get_scan_settings_db()
        last_scan_time = scan_settings.get("last_scan_time")
        payload["scan"] = {
            "interval_seconds": scan_settings.get("interval_seconds"),
            "last_scan_time": last_scan_time,
            "last_scan_at": _epoch_to_iso(last_scan_time),
        }
    except Exception:
        overall_status = "degraded"
        payload["scan"] = {
            "interval_seconds": None,
            "last_scan_time": None,
            "last_scan_at": None,
            "status": "unavailable",
        }

    payload["status"] = overall_status
    return payload
