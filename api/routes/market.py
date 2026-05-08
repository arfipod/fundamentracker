from __future__ import annotations

from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException

from services import market as market_service


def create_router(
    *,
    require_api_token: Callable[..., None],
    get_market_data_service: Callable[[], Any],
    metrics_map: dict[str, Any],
) -> APIRouter:
    router = APIRouter()

    @router.get("/search")
    def search_ticker(q: str):
        try:
            return market_service.search_symbols(get_market_data_service(), q)
        except Exception:
            return []

    @router.get("/data/providers/health", dependencies=[Depends(require_api_token)])
    def get_data_provider_health():
        try:
            return market_service.get_provider_health(get_market_data_service())
        except Exception as error:
            raise HTTPException(status_code=500, detail=str(error)) from error

    @router.get("/metrics/catalog")
    def get_metrics_catalog():
        return market_service.get_metrics_catalog()

    @router.get("/metric-current", dependencies=[Depends(require_api_token)])
    def get_metric_current(ticker: str, metric: str):
        try:
            return market_service.get_metric_current(
                get_market_data_service(),
                ticker=ticker,
                metric=metric,
                metrics_map=metrics_map,
            )
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        except Exception as error:
            raise HTTPException(status_code=500, detail=str(error)) from error

    @router.get("/history", dependencies=[Depends(require_api_token)])
    def get_history(ticker: str, metric: str, period: str = "1y"):
        try:
            return market_service.get_history(
                get_market_data_service(),
                ticker=ticker,
                metric=metric,
                period=period,
            )
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        except Exception as error:
            raise HTTPException(status_code=500, detail=str(error)) from error

    @router.get("/market-overview")
    def get_market_overview():
        try:
            return market_service.get_market_overview(get_market_data_service())
        except Exception as error:
            raise HTTPException(status_code=500, detail=str(error)) from error

    return router
