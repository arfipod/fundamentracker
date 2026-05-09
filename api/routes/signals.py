from __future__ import annotations

from typing import Any, Callable, Literal

from fastapi import APIRouter, Depends, HTTPException

from services import signals as signal_service


def create_router(
    *,
    require_api_token: Callable[..., None],
    get_db: Callable[[], Any],
) -> APIRouter:
    router = APIRouter()

    @router.get("/signals", dependencies=[Depends(require_api_token)])
    def get_signals(status: Literal["open", "all"] = "open", limit: int = 50):
        return signal_service.get_signals(get_db(), status=status, limit=limit)

    @router.patch("/signals/{signal_id}/acknowledge", dependencies=[Depends(require_api_token)])
    def acknowledge_signal(signal_id: str):
        signal = signal_service.acknowledge_signal(get_db(), signal_id)
        if signal is None:
            raise HTTPException(status_code=404, detail="Signal not found")
        return signal

    @router.patch("/signals/{signal_id}/dismiss", dependencies=[Depends(require_api_token)])
    def dismiss_signal(signal_id: str):
        signal = signal_service.dismiss_signal(get_db(), signal_id)
        if signal is None:
            raise HTTPException(status_code=404, detail="Signal not found")
        return signal

    return router
