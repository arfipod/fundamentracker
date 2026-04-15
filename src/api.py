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
from typing import Optional

SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

from config import METRICS_MAP, OPERATORS_MAP
from db import client as db
from scanner import run_fundamental_scan
from telegram_service import send_message, process_telegram_commands

app = FastAPI(title="FundamenTracker API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://fundamentracker.vercel.app", "*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


class ScanSettingsRequest(BaseModel):
    interval_seconds: int

class ToggleAlertRequest(BaseModel):
    is_active: bool


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


@app.get("/watchlist")
def get_watchlist():
    return db.get_watchlist()


@app.post("/add")
def add_watchlist_alert(payload: AddAlertRequest):
    metric = payload.metric.lower()
    operator = payload.operator

    if metric not in METRICS_MAP:
        raise HTTPException(status_code=400, detail=f"Invalid metric: {metric}")
    if operator not in OPERATORS_MAP:
        raise HTTPException(status_code=400, detail=f"Invalid operator: {operator}")

    symbol = payload.ticker.upper()
    
    import yfinance as yf
    try:
        t_info = yf.Ticker(symbol).info
        name = t_info.get("shortName", symbol)
        current_val = t_info.get(METRICS_MAP[metric], None)
    except:
        name = symbol
        current_val = None
        
    db.add_ticker_db(symbol, name)
    
    ref_val = current_val if payload.alert_type == "relative" else None
    db.add_alert_db(symbol, metric, operator, payload.value, payload.alert_type, ref_val)
    
    perform_scan()

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
    res = db.delete_ticker_db(ticker.upper())
    if not res:
        raise HTTPException(status_code=404, detail="Ticker not found")

    return {"message": "Ticker removed", "ticker": ticker.upper()}


@app.delete("/remove/{ticker}/{metric}")
def remove_watchlist_alert(ticker: str, metric: str):
    res = db.delete_alert_db(symbol=ticker.upper(), metric=metric.lower())
    if not res:
        raise HTTPException(status_code=404, detail="Alert not found")
        
    watchlist = db.get_watchlist()
    if ticker.upper() in watchlist and len(watchlist[ticker.upper()]["alerts"]) == 0:
        db.delete_ticker_db(ticker.upper())

    return {"message": "Alert removed"}


@app.put("/update")
def update_watchlist_alert(payload: UpdateAlertRequest):
    symbol = payload.ticker.upper()
    watchlist = db.get_watchlist()
    if symbol in watchlist:
        for a in watchlist[symbol]["alerts"]:
            if a["metric"] == payload.metric.lower():
                db.update_alert_target(a["id"], payload.value)
                return {"message": "Alert updated"}
                
    raise HTTPException(status_code=404, detail="Alert not found")


@app.post("/scan")
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


@app.put("/scan-settings")
def update_scan_settings(payload: ScanSettingsRequest):
    db.update_scan_settings_db(interval=payload.interval_seconds)
    return db.get_scan_settings_db()


@app.patch("/alerts/{alert_id}/toggle")
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
