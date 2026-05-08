from __future__ import annotations

from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException

from schemas.alerts import AddAlertRequest, UpdateAlertRequest
from services import watchlist as watchlist_service


def create_router(
    *,
    require_api_token: Callable[..., None],
    require_watchlist_access: Callable[..., None],
    get_db: Callable[[], Any],
    get_market_data_service: Callable[[], Any],
    metrics_map: dict[str, Any],
    operators_map: dict[str, Any],
    run_scan: Callable[[], None],
) -> APIRouter:
    router = APIRouter()

    @router.get("/watchlist", dependencies=[Depends(require_watchlist_access)])
    def get_watchlist():
        return watchlist_service.get_watchlist(get_db())

    @router.post("/add", dependencies=[Depends(require_api_token)])
    def add_watchlist_alert(payload: AddAlertRequest):
        try:
            return watchlist_service.add_watchlist_alert(
                db_client=get_db(),
                market_data_service=get_market_data_service(),
                payload=payload,
                metrics_map=metrics_map,
                operators_map=operators_map,
                run_scan=run_scan,
            )
        except watchlist_service.WatchlistValidationError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

    @router.delete("/remove/{ticker}", dependencies=[Depends(require_api_token)])
    def remove_watchlist_ticker(ticker: str):
        if not watchlist_service.remove_watchlist_ticker(get_db(), ticker):
            raise HTTPException(status_code=404, detail="Ticker not found")

        return {"message": "Ticker removed", "ticker": ticker.upper()}

    @router.delete("/remove/{ticker}/{metric}", dependencies=[Depends(require_api_token)], deprecated=True)
    def remove_watchlist_alert(ticker: str, metric: str):
        try:
            if not watchlist_service.remove_watchlist_alert(get_db(), ticker, metric):
                raise HTTPException(status_code=404, detail="Alert not found")
        except watchlist_service.WatchlistAlertNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except watchlist_service.WatchlistAmbiguousAlertError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

        return {"message": "Alert removed"}

    @router.put("/update", dependencies=[Depends(require_api_token)], deprecated=True)
    def update_watchlist_alert(payload: UpdateAlertRequest):
        try:
            if watchlist_service.update_watchlist_alert(get_db(), payload):
                return {"message": "Alert updated"}
        except watchlist_service.WatchlistAlertNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except watchlist_service.WatchlistAmbiguousAlertError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

        raise HTTPException(status_code=404, detail="Alert not found")

    return router
