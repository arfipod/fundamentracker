from __future__ import annotations

from cache import get_ticker_info

from config import METRICS_MAP, OPERATORS_MAP
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
            is_triggered = False
            if current_val is not None and alert["operator"] in OPERATORS_MAP:
                op_func = OPERATORS_MAP[alert["operator"]]
                
                # Check absolute vs relative logic
                if alert.get("alert_type") == "relative" and alert.get("reference_value") is not None:
                    # Target is percentage e.g. 5 means 5%
                    diff = ((current_val / alert["reference_value"]) - 1) * 100
                    is_triggered = op_func(diff, alert["target"])
                else:
                    is_triggered = op_func(current_val, alert["target"])
                
            status = "🔔 TRIGGERED" if alert.get("is_triggered", False) else "⏳ waiting"
            if not alert.get("is_active", True):
                 status = "🔇 MUTED"
            val_display = f" (Current: {current_val:.2f})" if current_val is not None else ""
            
            ref_info = f" [Ref: {alert['reference_value']:.2f}]" if alert.get("alert_type") == "relative" else ""
            type_symbol = "%" if alert.get("alert_type") == "relative" else ""
            
            message += f"  ↳ {alert['metric']} {alert['operator']} {alert['target']}{type_symbol} {ref_info}{val_display} [{status}]\n"
            
    return message
