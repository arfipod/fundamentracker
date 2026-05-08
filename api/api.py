from __future__ import annotations

import asyncio
import os
import secrets
import sys
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

from config import METRICS_MAP, OPERATORS_MAP, env_flag_enabled, get_cors_allowed_origins
from core.logging import configure_logging
from market_data.service import get_market_data_service
from repositories.factory import get_repository, is_postgres_backend, wait_for_database_ready
from routes.alerts import create_router as create_alerts_router
from routes.health import create_router as create_health_router
from routes.market import create_router as create_market_router
from routes.ops import create_router as create_ops_router
from routes.scans import create_router as create_scans_router
from routes.valuation import create_router as create_valuation_router
from routes.watchlist import create_router as create_watchlist_router
from schemas.alerts import (
    AddAlertRequest,
    ToggleAlertRequest,
    UpdateAlertByIdRequest,
    UpdateAlertRequest,
)
from schemas.scans import ScanSettingsRequest
from schemas.valuation import ValuationRequest
from services import alerts as alert_service
from services import health as health_service
from services import scans as scan_service

SERVICE_NAME = "fundamentracker-api"
configure_logging(service_name=SERVICE_NAME)

app = FastAPI(title="FundamenTracker API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_allowed_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

SERVICE_VERSION = os.getenv("FUNDAMENTRACKER_VERSION") or os.getenv("APP_VERSION")
bearer_scheme = HTTPBearer(auto_error=False)
db = get_repository()
market_data_service = get_market_data_service()
background_tasks = set()


def require_api_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> None:
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    expected_token = os.getenv("API_AUTH_TOKEN")
    if not expected_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API_AUTH_TOKEN is not configured",
        )

    if not secrets.compare_digest(credentials.credentials, expected_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_watchlist_access(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> None:
    if env_flag_enabled(os.getenv("READONLY_PUBLIC")):
        return

    require_api_token(credentials)


def require_ready_health_access(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> None:
    if env_flag_enabled(os.getenv("PUBLIC_READY_HEALTH")):
        return

    require_api_token(credentials)


def utc_timestamp() -> str:
    return health_service.utc_timestamp()


def perform_scan() -> None:
    scan_service.perform_scan(db)


def _find_alert_symbol(alert_id: str) -> str | None:
    return alert_service.find_alert_symbol(db, alert_id)


async def run_telegram_polling() -> None:
    await scan_service.run_telegram_polling()


async def run_periodic_scan() -> None:
    await scan_service.run_periodic_scan(db, lambda: perform_scan())


@app.on_event("startup")
async def startup_event():
    if is_postgres_backend():
        await asyncio.to_thread(wait_for_database_ready)

    periodic_scan_task = asyncio.create_task(run_periodic_scan())
    background_tasks.add(periodic_scan_task)

    telegram_polling_task = asyncio.create_task(run_telegram_polling())
    background_tasks.add(telegram_polling_task)


app.include_router(
    create_health_router(
        require_ready_health_access=require_ready_health_access,
        get_db=lambda: db,
        service_name=SERVICE_NAME,
        service_version=SERVICE_VERSION,
        timestamp_fn=utc_timestamp,
    )
)
app.include_router(
    create_valuation_router(
        require_api_token=require_api_token,
        get_market_data_service=lambda: market_data_service,
    )
)
app.include_router(
    create_watchlist_router(
        require_api_token=require_api_token,
        require_watchlist_access=require_watchlist_access,
        get_db=lambda: db,
        get_market_data_service=lambda: market_data_service,
        metrics_map=METRICS_MAP,
        operators_map=OPERATORS_MAP,
        run_scan=lambda: perform_scan(),
    )
)
app.include_router(
    create_alerts_router(
        require_api_token=require_api_token,
        get_db=lambda: db,
    )
)
app.include_router(
    create_scans_router(
        require_api_token=require_api_token,
        get_db=lambda: db,
        run_scan=lambda: perform_scan(),
    )
)
app.include_router(
    create_market_router(
        require_api_token=require_api_token,
        get_market_data_service=lambda: market_data_service,
        metrics_map=METRICS_MAP,
    )
)
app.include_router(
    create_ops_router(
        require_api_token=require_api_token,
        get_db=lambda: db,
        get_market_data_service=lambda: market_data_service,
        service_name=SERVICE_NAME,
        service_version=SERVICE_VERSION,
        timestamp_fn=utc_timestamp,
    )
)
