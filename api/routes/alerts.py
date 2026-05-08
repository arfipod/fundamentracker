from __future__ import annotations

from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException

from schemas.alerts import ToggleAlertRequest, UpdateAlertByIdRequest
from services import alerts as alert_service


def create_router(
    *,
    require_api_token: Callable[..., None],
    get_db: Callable[[], Any],
) -> APIRouter:
    router = APIRouter()

    @router.patch("/alerts/{alert_id}", dependencies=[Depends(require_api_token)])
    def update_alert_by_id(alert_id: str, payload: UpdateAlertByIdRequest):
        if not alert_service.update_alert_by_id(get_db(), alert_id, payload.value):
            raise HTTPException(status_code=404, detail="Alert not found")
        return {"message": "Alert updated"}

    @router.delete("/alerts/{alert_id}", dependencies=[Depends(require_api_token)])
    def delete_alert_by_id(alert_id: str):
        if not alert_service.delete_alert_by_id(get_db(), alert_id):
            raise HTTPException(status_code=404, detail="Alert not found")
        return {"message": "Alert removed"}

    @router.patch("/alerts/{alert_id}/toggle", dependencies=[Depends(require_api_token)])
    def toggle_alert(alert_id: str, payload: ToggleAlertRequest):
        if not alert_service.toggle_alert(get_db(), alert_id, payload.is_active):
            raise HTTPException(status_code=404, detail="Alert not found or failed to update")
        return {"message": "Alert status updated"}

    @router.get("/alert-history")
    def get_alert_history(limit: int = 50):
        return alert_service.get_alert_history(get_db(), limit=limit)

    return router
