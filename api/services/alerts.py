from __future__ import annotations

from typing import Any


def find_alert_symbol(db_client: Any, alert_id: str) -> str | None:
    watchlist = db_client.get_watchlist()
    if not isinstance(watchlist, dict):
        return None

    for symbol, details in watchlist.items():
        for alert in details.get("alerts", []):
            if str(alert.get("id")) == str(alert_id):
                return symbol
    return None


def update_alert_by_id(db_client: Any, alert_id: str, value: float) -> bool:
    return bool(db_client.update_alert_target(alert_id, value))


def delete_alert_by_id(db_client: Any, alert_id: str) -> bool:
    symbol = find_alert_symbol(db_client, alert_id)
    deleted = db_client.delete_alert_db(alert_id=alert_id)
    if not deleted:
        return False

    if symbol:
        watchlist = db_client.get_watchlist()
        if symbol in watchlist and len(watchlist[symbol]["alerts"]) == 0:
            db_client.delete_ticker_db(symbol)

    return True


def toggle_alert(db_client: Any, alert_id: str, is_active: bool) -> bool:
    return bool(db_client.toggle_alert_active(alert_id, is_active))


def get_alert_history(db_client: Any, limit: int = 50):
    return db_client.get_alert_history_db(limit=limit)
