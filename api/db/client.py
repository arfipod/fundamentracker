import os
import requests

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

def _req(method, endpoint, **kwargs):
    if not SUPABASE_URL or not SUPABASE_KEY:
        return [] if method == "GET" else None
    
    url = f"{SUPABASE_URL}/rest/v1/{endpoint}"
    headers = HEADERS.copy()
    if 'headers' in kwargs:
        headers.update(kwargs.pop('headers'))
        
    try:
        response = requests.request(method, url, headers=headers, **kwargs)
        response.raise_for_status()
        if method != 'DELETE':
            if response.text.strip() == "":
                return []
            return response.json()
        return True
    except requests.exceptions.RequestException as e:
        print(f"DB Error: {method} {url} - {e}")
        if hasattr(e, 'response') and e.response is not None:
             print("Details:", e.response.text)
        return [] if method == "GET" else None

def get_watchlist():
    tickers = _req("GET", "tickers") or []
    alerts = _req("GET", "alerts") or []
    
    watchlist = {}
    for t in tickers:
        watchlist[t["symbol"]] = {
            "name": t["name"],
            "alerts": []
        }
        
    for a in alerts:
        sym = a["ticker_symbol"]
        if sym in watchlist:
            watchlist[sym]["alerts"].append({
                "id": a["id"],
                "metric": a["metric"],
                "operator": a["operator"],
                "target": float(a["target_value"]) if a["target_value"] is not None else 0,
                "is_active": a["is_active"],
                "is_triggered": a["is_triggered"],
                "reference_value": float(a["reference_value"]) if a["reference_value"] is not None else None,
                "alert_type": a["alert_type"],
                "current_value": float(a["current_value"]) if a["current_value"] is not None else None
            })
            
    return watchlist

def get_alerts():
    return _req("GET", "alerts") or []

def get_tickers():
    return _req("GET", "tickers") or []

def add_ticker_db(symbol, company_name):
    headers = {"Prefer": "resolution=merge-duplicates, return=representation"}
    payload = {"symbol": symbol, "name": company_name}
    res = _req("POST", "tickers", json=payload, headers=headers)
    return res

def add_alert_db(symbol, metric, operator, target_value, alert_type="absolute", reference_value=None):
    payload = {
        "ticker_symbol": symbol,
        "metric": metric,
        "operator": operator,
        "target_value": target_value,
        "alert_type": alert_type,
        "reference_value": reference_value,
        "is_active": True,
        "is_triggered": False
    }
    headers = {"Prefer": "return=representation"}
    res = _req("POST", "alerts", json=payload, headers=headers)
    return res

def update_alert_target(alert_id, new_target):
    payload = {"target_value": float(new_target)}
    headers = {"Prefer": "return=representation"}
    return _req("PATCH", f"alerts?id=eq.{alert_id}", json=payload, headers=headers)

def toggle_alert_active(alert_id, is_active):
    payload = {"is_active": is_active}
    headers = {"Prefer": "return=representation"}
    return _req("PATCH", f"alerts?id=eq.{alert_id}", json=payload, headers=headers)

def update_alert_status(alert_id, is_triggered, current_value=None):
    payload = {"is_triggered": is_triggered}
    if current_value is not None:
        payload["current_value"] = float(current_value)
    headers = {"Prefer": "return=representation"}
    return _req("PATCH", f"alerts?id=eq.{alert_id}", json=payload, headers=headers)

def delete_alert_db(alert_id=None, symbol=None, metric=None):
    if alert_id:
        return _req("DELETE", f"alerts?id=eq.{alert_id}")
    elif symbol and metric:
        return _req("DELETE", f"alerts?ticker_symbol=eq.{symbol}&metric=eq.{metric}")
    return False

def delete_ticker_db(symbol):
    return _req("DELETE", f"tickers?symbol=eq.{symbol}")

def get_scan_settings_db():
    res = _req("GET", "scan_settings?id=eq.1")
    if res and len(res) > 0:
        return res[0]
    return {"interval_seconds": 0, "last_scan_time": 0}

def update_scan_settings_db(interval=None, last_scan_time=None):
    payload = {}
    if interval is not None:
        payload["interval_seconds"] = interval
    if last_scan_time is not None:
        payload["last_scan_time"] = last_scan_time
        
    headers = {"Prefer": "return=representation"}
    res = _req("PATCH", "scan_settings?id=eq.1", json=payload, headers=headers)
    if res and len(res) > 0:
        return res[0]
    return {}

def log_alert_history(alert_id, trigger_val, target_val):
    payload = {
        "alert_id": alert_id,
        "trigger_value": trigger_val,
        "target_value": target_val
    }
    headers = {"Prefer": "return=representation"}
    return _req("POST", "alert_history", json=payload, headers=headers)

def get_alert_history_db(limit=50):
    return _req("GET", f"alert_history?select=*,alerts(ticker_symbol,metric)&order=triggered_at.desc&limit={limit}") or []
