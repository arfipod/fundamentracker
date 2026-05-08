from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def live_payload(
    *,
    service_name: str,
    service_version: str | None,
    timestamp_fn=utc_timestamp,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "status": "ok",
        "service": service_name,
        "timestamp": timestamp_fn(),
    }
    if service_version:
        payload["version"] = service_version
    return payload


def ready_payload(
    *,
    database: dict[str, Any],
    service_name: str,
    service_version: str | None,
    timestamp_fn=utc_timestamp,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "status": "ok",
        "service": service_name,
        "timestamp": timestamp_fn(),
        "checks": {
            "configuration": {"status": "ok"},
            "database": database,
        },
    }
    if service_version:
        payload["version"] = service_version
    return payload


def ready_error_payload(
    *,
    error: Any,
    service_name: str,
    timestamp_fn=utc_timestamp,
) -> dict[str, Any]:
    return {
        "status": "error",
        "service": service_name,
        "timestamp": timestamp_fn(),
        "checks": {
            "database": {
                "status": "error",
                "backend": error.backend,
                "reason": error.reason,
                "detail": error.detail,
            }
        },
    }
