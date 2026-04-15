from __future__ import annotations

import os
import sys
from pathlib import Path

import requests
import asyncio
import time
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

from config import METRICS_MAP, OPERATORS_MAP
from supabase_db import load_state, save_state
from scanner import run_fundamental_scan
from state import ensure_state_shape
from telegram_service import send_message
from watchlist import add_ticker, remove_ticker, update_alert_target, remove_alert

app = FastAPI(title="FundamenTracker API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

state = ensure_state_shape(load_state())

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Adding this to allow vercel
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AddAlertRequest(BaseModel):
    ticker: str
    metric: str
    operator: str
    value: float


class UpdateAlertRequest(BaseModel):
    ticker: str
    metric: str
    value: float


class ScanSettingsRequest(BaseModel):
    interval_seconds: int


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(run_periodic_scan())

async def run_periodic_scan():
    while True:
        try:
            settings = state.get("scan_settings", {})
            interval = settings.get("interval_seconds", 0)
            if interval > 0:
                last_time = settings.get("last_scan_time", 0)
                now = time.time()
                if now - last_time >= interval:
                    token = os.getenv("TELEGRAM_TOKEN")
                    chat_id = os.getenv("TELEGRAM_CHAT_ID")
                    telegram_api = f"https://api.telegram.org/bot{token}" if token else ""

                    def send_telegram_alert(text: str) -> None:
                        if not token or not chat_id:
                            return
                        send_message(requests, telegram_api, chat_id, text)

                    run_fundamental_scan(state, send_telegram_alert)
                    state["scan_settings"]["last_scan_time"] = time.time()
                    save_state(state)
        except Exception as e:
            print(f"Error in background scan: {e}")
            
        await asyncio.sleep(60)


@app.get("/watchlist")
def get_watchlist():
    return state.get("watchlist", {})


@app.post("/add")
def add_watchlist_alert(payload: AddAlertRequest):
    metric = payload.metric.lower()
    operator = payload.operator

    if metric not in METRICS_MAP:
        raise HTTPException(status_code=400, detail=f"Invalid metric: {metric}")
    if operator not in OPERATORS_MAP:
        raise HTTPException(status_code=400, detail=f"Invalid operator: {operator}")

    symbol, name = add_ticker(state, payload.ticker, metric, operator, payload.value)
    save_state(state)

    return {
        "message": "Ticker added",
        "ticker": symbol,
        "name": name,
        "metric": metric,
        "operator": operator,
        "value": payload.value,
    }


@app.delete("/remove/{ticker}")
def remove_watchlist_ticker(ticker: str):
    removed, symbol = remove_ticker(state, ticker)
    if not removed:
        raise HTTPException(status_code=404, detail="Ticker not found")

    save_state(state)
    return {"message": "Ticker removed", "ticker": symbol}


@app.delete("/remove/{ticker}/{metric}")
def remove_watchlist_alert(ticker: str, metric: str):
    removed = remove_alert(state, ticker, metric)
    if not removed:
        raise HTTPException(status_code=404, detail="Alert not found")

    save_state(state)
    return {"message": "Alert removed"}


@app.put("/update")
def update_watchlist_alert(payload: UpdateAlertRequest):
    updated = update_alert_target(state, payload.ticker, payload.metric, payload.value)
    if not updated:
        raise HTTPException(status_code=404, detail="Alert not found")
    save_state(state)
    return {"message": "Alert updated"}


@app.post("/scan")
def scan_watchlist():
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    telegram_api = f"https://api.telegram.org/bot{token}" if token else ""

    def send_telegram_alert(text: str) -> None:
        if not token or not chat_id:
            return
        send_message(requests, telegram_api, chat_id, text)

    run_fundamental_scan(state, send_telegram_alert)
    save_state(state)

    return {"message": "Scan completed", "watchlist_size": len(state.get("watchlist", {}))}


@app.get("/scan-settings")
def get_scan_settings():
    return state.get("scan_settings", {"interval_seconds": 0, "last_scan_time": 0})

@app.put("/scan-settings")
def update_scan_settings(payload: ScanSettingsRequest):
    if "scan_settings" not in state:
        state["scan_settings"] = {"interval_seconds": 0, "last_scan_time": 0}
    state["scan_settings"]["interval_seconds"] = payload.interval_seconds
    save_state(state)
    return state["scan_settings"]


@app.get("/search")
def search_ticker(q: str):
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(f"https://query2.finance.yahoo.com/v1/finance/search?q={q}&quotesCount=5", headers=headers)
        if res.ok:
            data = res.json()
            quotes = data.get("quotes", [])
            return [{"symbol": quote.get("symbol"), "name": quote.get("shortname", quote.get("longname", ""))} for quote in quotes if "symbol" in quote and quote.get("quoteType") in ["EQUITY", "ETF", "CURRENCY", "CRYPTOCURRENCY"]]
    except Exception:
        pass
    return []
