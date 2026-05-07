from __future__ import annotations

import os
import secrets
import sys
from pathlib import Path
from datetime import datetime, timezone

import requests
import asyncio
import time
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from typing import Optional

SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

from config import METRICS_MAP, OPERATORS_MAP, env_flag_enabled, get_cors_allowed_origins
from db import client as db
from market_data.service import get_market_data_service
from scanner import run_fundamental_scan
from telegram_service import send_message, process_telegram_commands

app = FastAPI(title="FundamenTracker API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_allowed_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

SERVICE_NAME = "fundamentracker-api"
SERVICE_VERSION = os.getenv("FUNDAMENTRACKER_VERSION") or os.getenv("APP_VERSION")
bearer_scheme = HTTPBearer(auto_error=False)
market_data_service = get_market_data_service()


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


def utc_timestamp():
    return datetime.now(timezone.utc).isoformat()


@app.get("/health/live")
def health_live():
    payload = {
        "status": "ok",
        "service": SERVICE_NAME,
        "timestamp": utc_timestamp(),
    }
    if SERVICE_VERSION:
        payload["version"] = SERVICE_VERSION
    return payload


@app.get("/health/ready")
def health_ready():
    try:
        database = db.check_database_connectivity()
    except db.DatabaseHealthError as error:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "error",
                "service": SERVICE_NAME,
                "timestamp": utc_timestamp(),
                "checks": {
                    "database": {
                        "status": "error",
                        "backend": error.backend,
                        "reason": error.reason,
                        "detail": error.detail,
                    }
                },
            },
        ) from error

    payload = {
        "status": "ok",
        "service": SERVICE_NAME,
        "timestamp": utc_timestamp(),
        "checks": {
            "configuration": {"status": "ok"},
            "database": database,
        },
    }
    if SERVICE_VERSION:
        payload["version"] = SERVICE_VERSION
    return payload


class AddAlertRequest(BaseModel):
    ticker: str
    metric: str
    operator: str
    value: float
    alert_type: Optional[str] = "absolute"


class UpdateAlertRequest(BaseModel):
    ticker: str
    metric: str
    value: float


class UpdateAlertByIdRequest(BaseModel):
    value: float


class ScanSettingsRequest(BaseModel):
    interval_seconds: int

class ToggleAlertRequest(BaseModel):
    is_active: bool

class ValuationRequest(BaseModel):
    ticker: str

@app.post("/ai-valuation", dependencies=[Depends(require_api_token)])
def ai_valuation(payload: ValuationRequest):
    import os
    try:
        from google import genai
    except ImportError:
        raise HTTPException(status_code=500, detail="Google GenAI library not installed")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not configured. Please set it in your environment.")

    client = genai.Client(api_key=api_key)
    
    try:
        symbol = payload.ticker.upper()
        info = market_data_service.get_quote(symbol)
        
        stats_str = f"Company: {info.get('longName', symbol)}\n"
        stats_str += f"Sector: {info.get('sector', 'N/A')}\n"
        stats_str += f"Industry: {info.get('industry', 'N/A')}\n"
        stats_str += f"Current Price: {info.get('currentPrice', 'N/A')}\n"
        stats_str += f"Trailing P/E: {info.get('trailingPE', 'N/A')}\n"
        stats_str += f"Forward P/E: {info.get('forwardPE', 'N/A')}\n"
        stats_str += f"Price to Book: {info.get('priceToBook', 'N/A')}\n"
        stats_str += f"Return on Equity: {info.get('returnOnEquity', 'N/A')}\n"
        stats_str += f"Debt to Equity: {info.get('debtToEquity', 'N/A')}\n"
        stats_str += f"Profit Margin: {info.get('profitMargins', 'N/A')}\n"
        stats_str += f"Dividend Yield: {info.get('dividendYield', 'N/A')}\n"
        
        prompt = f"You are a financial analyst. Based on the following current fundamental data for {symbol}:\n\n{stats_str}\n\nProvide a concise (3-4 sentences) valuation analysis. Is the stock undervalued, fairly valued, or overvalued compared to historical norms and its sector? Be objective."
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        return {"analysis": response.text}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Valuation error: {str(e)}")


def perform_scan():
    print("\n--- Executing Fundamental Scan ---", flush=True)
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    telegram_api = f"https://api.telegram.org/bot{token}" if token else ""
    def send_telegram_alert(text: str) -> None:
        if not token or not chat_id:
            return
        send_message(requests, telegram_api, chat_id, text)
        
    run_fundamental_scan(send_telegram_alert)
    db.update_scan_settings_db(last_scan_time=int(time.time()))


background_tasks = set()

@app.on_event("startup")
async def startup_event():
    if db.is_postgres_backend():
        await asyncio.to_thread(db.wait_for_database_ready)

    task1 = asyncio.create_task(run_periodic_scan())
    background_tasks.add(task1)
    task2 = asyncio.create_task(run_telegram_polling())
    background_tasks.add(task2)


async def run_telegram_polling():
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        return
        
    telegram_api = f"https://api.telegram.org/bot{token}"
    
    while True:
        try:
            process_telegram_commands(requests, telegram_api)
        except Exception as e:
            print(f"Telegram polling error: {e}")
        
        await asyncio.sleep(5)


async def run_periodic_scan():
    while True:
        try:
            settings = db.get_scan_settings_db()
            interval = settings.get("interval_seconds", 0)
            if interval > 0:
                last_time = settings.get("last_scan_time", 0)
                now = int(time.time())
                if now - last_time >= interval:
                    perform_scan()
        except Exception as e:
            print(f"Error in background scan: {e}")
            
        await asyncio.sleep(5)


@app.get("/watchlist", dependencies=[Depends(require_watchlist_access)])
def get_watchlist():
    return db.get_watchlist()


@app.post("/add", dependencies=[Depends(require_api_token)])
def add_watchlist_alert(payload: AddAlertRequest):
    metric = payload.metric.lower()
    operator = payload.operator
    alert_type = payload.alert_type or "absolute"

    if metric not in METRICS_MAP:
        raise HTTPException(status_code=400, detail=f"Invalid metric: {metric}")
    if operator not in OPERATORS_MAP:
        raise HTTPException(status_code=400, detail=f"Invalid operator: {operator}")
    if alert_type not in {"absolute", "relative"}:
        raise HTTPException(status_code=400, detail=f"Invalid alert_type: {alert_type}")

    symbol = payload.ticker.upper()
    
    try:
        quote = market_data_service.get_quote(symbol)
        name = quote.get("shortName", quote.get("name", symbol))
        current_val = market_data_service.get_metric(symbol, metric)
    except Exception:
        name = symbol
        current_val = None
        
    db.add_ticker_db(symbol, name)
    
    ref_val = current_val if alert_type == "relative" else None
    db.add_alert_db(symbol, metric, operator, payload.value, alert_type, ref_val)
    
    perform_scan()

    return {
        "message": "Ticker added",
        "ticker": symbol,
        "name": name,
        "metric": metric,
        "operator": operator,
        "value": payload.value,
        "alert_type": alert_type,
        "reference_value": ref_val,
    }


@app.delete("/remove/{ticker}", dependencies=[Depends(require_api_token)])
def remove_watchlist_ticker(ticker: str):
    res = db.delete_ticker_db(ticker.upper())
    if not res:
        raise HTTPException(status_code=404, detail="Ticker not found")

    return {"message": "Ticker removed", "ticker": ticker.upper()}


@app.delete("/remove/{ticker}/{metric}", dependencies=[Depends(require_api_token)], deprecated=True)
def remove_watchlist_alert(ticker: str, metric: str):
    res = db.delete_alert_db(symbol=ticker.upper(), metric=metric.lower())
    if not res:
        raise HTTPException(status_code=404, detail="Alert not found")
        
    watchlist = db.get_watchlist()
    if ticker.upper() in watchlist and len(watchlist[ticker.upper()]["alerts"]) == 0:
        db.delete_ticker_db(ticker.upper())

    return {"message": "Alert removed"}


@app.put("/update", dependencies=[Depends(require_api_token)], deprecated=True)
def update_watchlist_alert(payload: UpdateAlertRequest):
    symbol = payload.ticker.upper()
    watchlist = db.get_watchlist()
    if symbol in watchlist:
        for a in watchlist[symbol]["alerts"]:
            if a["metric"] == payload.metric.lower():
                db.update_alert_target(a["id"], payload.value)
                return {"message": "Alert updated"}
                
    raise HTTPException(status_code=404, detail="Alert not found")


def _find_alert_symbol(alert_id: str) -> str | None:
    watchlist = db.get_watchlist()
    if not isinstance(watchlist, dict):
        return None
    for symbol, details in watchlist.items():
        for alert in details.get("alerts", []):
            if str(alert.get("id")) == str(alert_id):
                return symbol
    return None


@app.patch("/alerts/{alert_id}", dependencies=[Depends(require_api_token)])
def update_alert_by_id(alert_id: str, payload: UpdateAlertByIdRequest):
    res = db.update_alert_target(alert_id, payload.value)
    if not res:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"message": "Alert updated"}


@app.delete("/alerts/{alert_id}", dependencies=[Depends(require_api_token)])
def delete_alert_by_id(alert_id: str):
    symbol = _find_alert_symbol(alert_id)
    res = db.delete_alert_db(alert_id=alert_id)
    if not res:
        raise HTTPException(status_code=404, detail="Alert not found")

    if symbol:
        watchlist = db.get_watchlist()
        if symbol in watchlist and len(watchlist[symbol]["alerts"]) == 0:
            db.delete_ticker_db(symbol)

    return {"message": "Alert removed"}


@app.post("/scan", dependencies=[Depends(require_api_token)])
def scan_watchlist():
    perform_scan()
    return {"message": "Scan completed"}


@app.get("/scan-settings")
def get_scan_settings():
    return db.get_scan_settings_db()


@app.get("/server-time")
def get_server_time():
    import time
    return {"server_time": time.time()}


@app.put("/scan-settings", dependencies=[Depends(require_api_token)])
def update_scan_settings(payload: ScanSettingsRequest):
    db.update_scan_settings_db(interval=payload.interval_seconds)
    return db.get_scan_settings_db()


@app.patch("/alerts/{alert_id}/toggle", dependencies=[Depends(require_api_token)])
def toggle_alert(alert_id: str, payload: ToggleAlertRequest):
    res = db.toggle_alert_active(alert_id, payload.is_active)
    if not res:
        raise HTTPException(status_code=404, detail="Alert not found or failed to update")
    return {"message": "Alert status updated"}


@app.get("/alert-history")
def get_alert_history(limit: int = 50):
    return db.get_alert_history_db(limit=limit)


@app.get("/search")
def search_ticker(q: str):
    try:
        return market_data_service.search_symbols(q)
    except Exception:
        return []


@app.get("/data/providers/health")
def get_data_provider_health():
    try:
        return market_data_service.get_provider_health()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metric-current")
def get_metric_current(ticker: str, metric: str):
    try:
        metric_name = metric.lower()
        service_metric = metric_name if metric_name in METRICS_MAP else "price"
        snapshot = market_data_service.get_metric_snapshot(ticker.upper(), service_metric)
        return {
            "ticker": ticker.upper(),
            "metric": metric,
            "value": snapshot.get("value"),
            "stale": snapshot.get("stale", False),
            "source": snapshot.get("source"),
            "as_of_date": snapshot.get("as_of_date"),
            "fetched_at": snapshot.get("fetched_at"),
            "expires_at": snapshot.get("expires_at"),
            "confidence": snapshot.get("confidence"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/history")
def get_history(ticker: str, metric: str, period: str = "1y"):
    try:
        return market_data_service.get_metric_history(ticker.upper(), metric, period)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/market-overview")
def get_market_overview():
    tickers = ["SPY", "QQQ", "DIA"]
    overview = []
    try:
        for ticker in tickers:
            try:
                history = market_data_service.get_price_history(ticker, "2d")
                values = [point["value"] for point in history if point.get("value") is not None]
                if len(values) >= 2:
                    current = values[-1]
                    previous = values[-2]
                    change = ((current - previous) / previous) * 100
                    overview.append({"symbol": ticker, "current": float(current), "change_percent": float(change)})
                elif len(values) == 1:
                    overview.append({"symbol": ticker, "current": float(values[-1]), "change_percent": 0.0})
            except Exception as e:
                print(f"Error fetching {ticker}: {e}")
        return overview
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
