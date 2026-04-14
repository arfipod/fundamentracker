from __future__ import annotations

import yfinance as yf

from config import METRICS_MAP, OPERATORS_MAP


import requests

def get_yf_session():
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0'})
    return session

def fetch_company_name(ticker: str) -> str:
    info = yf.Ticker(ticker, session=get_yf_session()).info
    return info.get("shortName", ticker)


def fetch_metric(ticker: str, metric_name: str) -> float | None:
    try:
        if metric_name not in METRICS_MAP:
            return None
        yf_key = METRICS_MAP[metric_name]
        ticker_info = yf.Ticker(ticker, session=get_yf_session()).info
        return ticker_info.get(yf_key)
    except Exception:
        return None


def parse_trigger(value: str) -> float:
    trigger = float(value)
    # Removing > 0 constraint as some metrics can be negative
    return trigger


def add_ticker(state: dict, ticker: str, metric: str, operator: str, target: float) -> tuple[str, str]:
    symbol = ticker.upper()

    if symbol not in state["watchlist"]:
        name = fetch_company_name(symbol)
        state["watchlist"][symbol] = {
            "name": name,
            "alerts": [],
        }
    else:
        name = state["watchlist"][symbol]["name"]

    state["watchlist"][symbol]["alerts"].append({
        "metric": metric,
        "operator": operator,
        "target": target,
        "is_triggered": False,
    })

    return symbol, name


def remove_ticker(state: dict, ticker: str) -> tuple[bool, str]:
    symbol = ticker.upper()

    if symbol in state["watchlist"]:
        del state["watchlist"][symbol]
        return True, symbol

    return False, symbol


def format_watchlist_message(state: dict) -> str:
    if not state["watchlist"]:
        return "📭 Watchlist empty."

    message = "📌 *Watchlist:*\n"
    for ticker, details in state["watchlist"].items():
        message += f"- *{details['name']}* ({ticker})\n"
        for alert in details.get("alerts", []):
            current_val = fetch_metric(ticker, alert["metric"])
            val_display = f" (Current: {current_val:.2f})" if current_val is not None else ""
            message += f"  ↳ {alert['metric']} {alert['operator']} {alert['target']}{val_display}\n"
    return message


def format_alerts_message(state: dict) -> str:
    if not state["watchlist"]:
        return "🔕 No alerts configured."

    message = "🚨 *Alert Configuration:*\n"
    for ticker, details in state["watchlist"].items():
        message += f"- *{details['name']}* ({ticker})\n"
        for alert in details.get("alerts", []):
            current_val = fetch_metric(ticker, alert["metric"])
            
            # Determine status based on current metric vs target
            is_triggered = False
            if current_val is not None and alert["operator"] in OPERATORS_MAP:
                op_func = OPERATORS_MAP[alert["operator"]]
                is_triggered = op_func(current_val, alert["target"])
                
            status = "🔔 TRIGGERED" if is_triggered else "⏳ waiting"
            val_display = f" (Current: {current_val:.2f})" if current_val is not None else ""
            
            message += f"  ↳ {alert['metric']} {alert['operator']} {alert['target']}{val_display} [{status}]\n"
            
    return message
