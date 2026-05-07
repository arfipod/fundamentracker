from __future__ import annotations

from cache import get_ticker_info

from alert_evaluator import calculate_relative_diff, evaluate_alert
from config import METRICS_MAP
import requests

def fetch_company_name(ticker: str) -> str:
    info = get_ticker_info(ticker)
    return info.get("shortName", ticker)


def fetch_metric(ticker: str, metric_name: str) -> float | None:
    try:
        if metric_name not in METRICS_MAP:
            return None
        yf_key = METRICS_MAP[metric_name]
        ticker_info = get_ticker_info(ticker)
        return ticker_info.get(yf_key)
    except Exception:
        return None


def format_watchlist_message(db) -> str:
    watchlist = db.get_watchlist()
    if not watchlist:
        return "📭 Watchlist empty."

    message = "📌 *Watchlist:*\n"
    for ticker, details in list(watchlist.items()):
        message += f"- *{details['name']}* ({ticker})\n"
        for alert in details.get("alerts", []):
            current_val = fetch_metric(ticker, alert["metric"])
            val_display = f" (Current: {current_val:.2f})" if current_val is not None else ""
            message += f"  ↳ {alert['metric']} {alert['operator']} {alert['target']}{val_display}\n"
    return message


def format_alerts_message(db) -> str:
    watchlist = db.get_watchlist()
    if not watchlist:
        return "🔕 No alerts configured."

    message = "🚨 *Alert Configuration:*\n"
    for ticker, details in list(watchlist.items()):
        message += f"- *{details['name']}* ({ticker})\n"
        for alert in details.get("alerts", []):
            current_val = fetch_metric(ticker, alert["metric"])
            
            # Determine status based on current metric vs target
            is_triggered = evaluate_alert(
                current_val,
                alert["target"],
                alert["operator"],
                alert.get("alert_type"),
                alert.get("reference_value"),
            )
                
            status = "🔔 TRIGGERED" if is_triggered else "⏳ waiting"
            if not alert.get("is_active", True):
                 status = "🔇 MUTED"
            val_display = f" (Current: {current_val:.2f})" if current_val is not None else ""
            
            reference_value = alert.get("reference_value")
            ref_info = f" [Ref: {reference_value:.2f}]" if alert.get("alert_type") == "relative" and reference_value is not None else ""
            diff = calculate_relative_diff(current_val, alert.get("reference_value")) if alert.get("alert_type") == "relative" else None
            diff_info = f" [Diff: {diff:.2f}%]" if diff is not None else ""
            type_symbol = "%" if alert.get("alert_type") == "relative" else ""
            
            message += f"  ↳ {alert['metric']} {alert['operator']} {alert['target']}{type_symbol} {ref_info}{diff_info}{val_display} [{status}]\n"
            
    return message
