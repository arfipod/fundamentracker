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

class ValuationRequest(BaseModel):
    ticker: str

@app.post("/ai-valuation")
def ai_valuation(payload: ValuationRequest):
    import os
    import yfinance as yf
    try:
        from google import genai
    except ImportError:
        raise HTTPException(status_code=500, detail="Google GenAI library not installed")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not configured. Please set it in your environment.")

    client = genai.Client(api_key=api_key)
    
    try:
        t = yf.Ticker(payload.ticker.upper())
        info = t.info
        
        stats_str = f"Company: {info.get('longName', payload.ticker)}\n"
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
        
        prompt = f"You are a financial analyst. Based on the following current fundamental data for {payload.ticker.upper()}:\n\n{stats_str}\n\nProvide a concise (3-4 sentences) valuation analysis. Is the stock undervalued, fairly valued, or overvalued compared to historical norms and its sector? Be objective."
        
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


@app.get("/metric-current")
def get_metric_current(ticker: str, metric: str):
    import yfinance as yf
    try:
        t = yf.Ticker(ticker.upper())
        if metric.lower() == "roic":
            # Just grab the last available from the helper
            from datetime import datetime, timedelta
            import pandas as pd
            # Create a dummy index of last 2 days
            idx = pd.date_range(end=datetime.now(), periods=2, freq='D')
            series = _get_historical_fundamental(t, "roic", idx)
            if series.isna().all():
                val = None
            else:
                val = float(series.iloc[-1])
            return {"ticker": ticker.upper(), "metric": metric, "value": val}
            
        metric_key = METRICS_MAP.get(metric.lower(), "currentPrice")
        t_info = t.info
        val = t_info.get(metric_key)
        if val is not None and metric.lower() in ["profitmargins", "operatingmargins", "roe"]:
            val *= 100
            
        return {"ticker": ticker.upper(), "metric": metric, "value": val}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _get_historical_fundamental(t, metric_name, hist_index):
    import pandas as pd
    try:
        q_inc = t.quarterly_incomestmt.T if t.quarterly_incomestmt is not None else pd.DataFrame()
        q_bal = t.quarterly_balancesheet.T if t.quarterly_balancesheet is not None else pd.DataFrame()
        q_df = pd.concat([q_inc, q_bal], axis=1).sort_index()
    except Exception:
        q_df = pd.DataFrame()
        
    if q_df.empty:
        return pd.Series(index=hist_index, dtype=float)

    values = []
    dates = []
    
    for date, row in q_df.iterrows():
        val = None
        if metric_name == "roe":
            ni = row.get("Net Income", 0)
            eq = row.get("Stockholders Equity", 0)
            if pd.notna(ni) and pd.notna(eq) and eq != 0:
                val = (ni / eq) * 100
                
        elif metric_name == "roic":
            ebit = row.get("EBIT", 0)
            if pd.isna(ebit):
                pi = row.get("Pretax Income", 0)
                ie = row.get("Interest Expense", 0)
                ebit = (pi if pd.notna(pi) else 0) + (ie if pd.notna(ie) else 0)
                
            tp = row.get("Tax Provision", 0)
            pi = row.get("Pretax Income", 0)
            tax_rate = tp / pi if pd.notna(tp) and pd.notna(pi) and pi != 0 else 0.21
            nopat = ebit * (1 - tax_rate)
            
            debt = row.get("Total Debt", 0)
            eq = row.get("Stockholders Equity", 0)
            if pd.isna(debt): debt = 0
            if pd.isna(eq): eq = 0
            
            if (debt + eq) != 0:
                val = (nopat / (debt + eq)) * 100
                
        elif metric_name == "debttoequity":
            debt = row.get("Total Debt", 0)
            eq = row.get("Stockholders Equity", 0)
            if pd.notna(debt) and pd.notna(eq) and eq != 0:
                val = debt / eq
                
        elif metric_name == "profitmargins":
            ni = row.get("Net Income", 0)
            tr = row.get("Total Revenue", 0)
            if pd.notna(ni) and pd.notna(tr) and tr != 0:
                val = (ni / tr) * 100
                
        elif metric_name == "operatingmargins":
            oi = row.get("Operating Income", 0)
            tr = row.get("Total Revenue", 0)
            if pd.notna(oi) and pd.notna(tr) and tr != 0:
                val = (oi / tr) * 100

        if val is not None:
            values.append(val)
            dates.append(date)
            
    if not values:
        return pd.Series(index=hist_index, dtype=float)
        
    series = pd.Series(values, index=dates).sort_index()
    series.index = pd.to_datetime(series.index)
    if hist_index.tz is not None and series.index.tz is None:
        series.index = series.index.tz_localize(hist_index.tz)
        
    combined = pd.concat([pd.Series(index=hist_index, dtype=float), series], axis=1)
    combined = combined.iloc[:, 1].ffill()
    return combined.loc[hist_index]

@app.get("/history")
def get_history(ticker: str, metric: str, period: str = "1y"):
    import yfinance as yf
    import pandas as pd
    try:
        t = yf.Ticker(ticker.upper())
        hist = t.history(period=period)
        if hist.empty:
            return []
        
        data = []
        metric = metric.lower()
        
        if metric == 'price':
            for date, row in hist.iterrows():
                data.append({"date": date.strftime("%Y-%m-%d"), "value": row["Close"]})
            return data

        t_info = t.info
        
        if metric == "pe":
            eps = t_info.get("trailingEps")
            if eps in (None, 0):
                raise HTTPException(status_code=400, detail="No valid EPS data for PE calculation")
            for date, row in hist.iterrows():
                data.append({"date": date.strftime("%Y-%m-%d"), "value": row["Close"] / eps})
                
        elif metric == "fpe":
            f_eps = t_info.get("forwardEps")
            if f_eps in (None, 0):
                raise HTTPException(status_code=400, detail="No valid forward EPS data")
            for date, row in hist.iterrows():
                data.append({"date": date.strftime("%Y-%m-%d"), "value": row["Close"] / f_eps})
                
        elif metric == "pb":
            bvps = t_info.get("bookValue")
            if bvps in (None, 0):
                raise HTTPException(status_code=400, detail="No valid book value data")
            for date, row in hist.iterrows():
                data.append({"date": date.strftime("%Y-%m-%d"), "value": row["Close"] / bvps})
                
        elif metric == "evebitda":
            shares = t_info.get("sharesOutstanding")
            debt = t_info.get("totalDebt", 0)
            cash = t_info.get("totalCash", 0)
            ebitda = t_info.get("ebitda")
            
            if not shares or not ebitda or ebitda == 0:
                raise HTTPException(status_code=400, detail="No valid data for EV/EBITDA calculation")
                
            net_debt = debt - cash
            for date, row in hist.iterrows():
                ev = row["Close"] * shares + net_debt
                data.append({"date": date.strftime("%Y-%m-%d"), "value": ev / ebitda})
                
        elif metric in ["roe", "roic", "debttoequity", "profitmargins", "operatingmargins"]:
            fund_series = _get_historical_fundamental(t, metric, hist.index)
            if fund_series.isna().all():
                # Fallback to current values if available
                current_val = t_info.get(METRICS_MAP.get(metric))
                if current_val is None:
                    raise HTTPException(status_code=400, detail=f"No {metric.upper()} data available")
                # Return constant line
                if metric in ["profitmargins", "operatingmargins", "roe"]:
                    current_val *= 100
                for date, row in hist.iterrows():
                    data.append({"date": date.strftime("%Y-%m-%d"), "value": current_val})
            else:
                for date, val in fund_series.items():
                    if pd.notna(val):
                        data.append({"date": date.strftime("%Y-%m-%d"), "value": float(val)})

        elif metric == "dividendyield":
            div = t_info.get("trailingAnnualDividendRate") or t_info.get("dividendRate")
            if not div:
                raise HTTPException(status_code=400, detail="No dividend data available")
            for date, row in hist.iterrows():
                data.append({"date": date.strftime("%Y-%m-%d"), "value": (div / row["Close"]) * 100})
                
        elif metric == "payoutratio":
            pr = t_info.get("payoutRatio")
            if pr is None:
                raise HTTPException(status_code=400, detail="No payout ratio data available")
            for date, row in hist.iterrows():
                data.append({"date": date.strftime("%Y-%m-%d"), "value": pr * 100})

        else:
            raise HTTPException(status_code=400, detail="Unsupported metric for history")

        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/market-overview")
def get_market_overview():
    import yfinance as yf
    tickers = ["SPY", "QQQ", "DIA"]
    overview = []
    try:
        data = yf.download(tickers, period="2d", interval="1d", group_by="ticker", threads=True, progress=False)
        for t in tickers:
            try:
                if t in data:
                    closes = data[t]["Close"].dropna()
                else:
                    # Depending on yf version, single ticker download format might differ, but multiple usually has ticker as top level
                    closes = data["Close"][t].dropna()
                
                if len(closes) >= 2:
                    current = closes.iloc[-1]
                    previous = closes.iloc[-2]
                    change = ((current - previous) / previous) * 100
                    overview.append({"symbol": t, "current": float(current), "change_percent": float(change)})
                elif len(closes) == 1:
                    overview.append({"symbol": t, "current": float(closes.iloc[-1]), "change_percent": 0.0})
            except Exception as e:
                print(f"Error fetching {t}: {e}")
        return overview
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
