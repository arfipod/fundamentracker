from __future__ import annotations

from typing import Any, Callable

from fastapi import APIRouter, Depends

from services import ops as ops_service


def create_router(
    *,
    require_api_token: Callable[..., None],
    get_db: Callable[[], Any],
    get_market_data_service: Callable[[], Any],
    service_name: str,
    service_version: str | None,
    timestamp_fn: Callable[[], str],
) -> APIRouter:
    router = APIRouter()

    @router.get("/ops/status", dependencies=[Depends(require_api_token)])
    def get_ops_status():
        return ops_service.status_payload(
            db_client=get_db(),
            market_data_service=get_market_data_service(),
            service_name=service_name,
            service_version=service_version,
            timestamp_fn=timestamp_fn,
        )

    return router
