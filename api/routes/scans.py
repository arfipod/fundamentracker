from __future__ import annotations

import time
from typing import Any, Callable

from fastapi import APIRouter, Depends

from schemas.scans import ScanSettingsRequest


def create_router(
    *,
    require_api_token: Callable[..., None],
    get_db: Callable[[], Any],
    run_scan: Callable[[], None],
) -> APIRouter:
    router = APIRouter()

    @router.post("/scan", dependencies=[Depends(require_api_token)])
    def scan_watchlist():
        run_scan()
        return {"message": "Scan completed"}

    @router.get("/scan-settings", dependencies=[Depends(require_api_token)])
    def get_scan_settings():
        return get_db().get_scan_settings_db()

    @router.get("/server-time")
    def get_server_time():
        return {"server_time": time.time()}

    @router.put("/scan-settings", dependencies=[Depends(require_api_token)])
    def update_scan_settings(payload: ScanSettingsRequest):
        db_client = get_db()
        db_client.update_scan_settings_db(interval=payload.interval_seconds)
        return db_client.get_scan_settings_db()

    return router
