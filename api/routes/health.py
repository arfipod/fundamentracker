from __future__ import annotations

from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException

from services import health as health_service


def create_router(
    *,
    require_ready_health_access: Callable[..., None],
    get_db: Callable[[], Any],
    service_name: str,
    service_version: str | None,
    timestamp_fn: Callable[[], str],
) -> APIRouter:
    router = APIRouter()

    @router.get("/health/live")
    def health_live():
        return health_service.live_payload(
            service_name=service_name,
            service_version=service_version,
            timestamp_fn=timestamp_fn,
        )

    @router.get("/health/ready", dependencies=[Depends(require_ready_health_access)])
    def health_ready():
        db_client = get_db()
        try:
            database = db_client.check_database_connectivity()
        except db_client.DatabaseHealthError as error:
            raise HTTPException(
                status_code=503,
                detail=health_service.ready_error_payload(
                    error=error,
                    service_name=service_name,
                    timestamp_fn=timestamp_fn,
                ),
            ) from error

        return health_service.ready_payload(
            database=database,
            service_name=service_name,
            service_version=service_version,
            timestamp_fn=timestamp_fn,
        )

    return router
