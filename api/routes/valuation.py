from __future__ import annotations

from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException

from schemas.valuation import ValuationRequest, ValuationResponse
from services import valuation as valuation_service


def create_router(
    *,
    require_api_token: Callable[..., None],
    get_market_data_service: Callable[[], Any],
) -> APIRouter:
    router = APIRouter()

    @router.post(
        "/ai-valuation",
        response_model=ValuationResponse,
        dependencies=[Depends(require_api_token)],
    )
    def ai_valuation(payload: ValuationRequest):
        try:
            return valuation_service.generate_ai_valuation(
                get_market_data_service(),
                payload.ticker,
            )
        except valuation_service.GenAILibraryNotInstalledError as error:
            raise HTTPException(status_code=500, detail=str(error)) from error
        except valuation_service.GeminiApiKeyNotConfiguredError as error:
            raise HTTPException(status_code=500, detail=str(error)) from error
        except valuation_service.InvalidAIValuationResponseError as error:
            raise HTTPException(status_code=502, detail=str(error)) from error
        except HTTPException:
            raise
        except Exception as error:
            raise HTTPException(status_code=500, detail=f"AI Valuation error: {str(error)}") from error

    return router
