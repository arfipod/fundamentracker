from __future__ import annotations

from typing import Any, Callable

from schemas.alerts import AddAlertRequest, UpdateAlertRequest


class WatchlistValidationError(ValueError):
    pass


def get_watchlist(db_client: Any):
    return db_client.get_watchlist()


def add_watchlist_alert(
    *,
    db_client: Any,
    market_data_service: Any,
    payload: AddAlertRequest,
    metrics_map: dict[str, Any],
    operators_map: dict[str, Any],
    run_scan: Callable[[], None],
) -> dict[str, Any]:
    metric = payload.metric.lower()
    operator = payload.operator
    alert_type = payload.alert_type or "absolute"

    if metric not in metrics_map:
        raise WatchlistValidationError(f"Invalid metric: {metric}")
    if operator not in operators_map:
        raise WatchlistValidationError(f"Invalid operator: {operator}")
    if alert_type not in {"absolute", "relative"}:
        raise WatchlistValidationError(f"Invalid alert_type: {alert_type}")

    symbol = payload.ticker.upper()

    try:
        quote = market_data_service.get_quote(symbol)
        name = quote.get("shortName", quote.get("name", symbol))
        current_val = market_data_service.get_metric(symbol, metric)
    except Exception:
        name = symbol
        current_val = None

    db_client.add_ticker_db(symbol, name)

    ref_val = current_val if alert_type == "relative" else None
    db_client.add_alert_db(symbol, metric, operator, payload.value, alert_type, ref_val)

    run_scan()

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


def remove_watchlist_ticker(db_client: Any, ticker: str) -> bool:
    return bool(db_client.delete_ticker_db(ticker.upper()))


def remove_watchlist_alert(db_client: Any, ticker: str, metric: str) -> bool:
    deleted = db_client.delete_alert_db(symbol=ticker.upper(), metric=metric.lower())
    if not deleted:
        return False

    watchlist = db_client.get_watchlist()
    if ticker.upper() in watchlist and len(watchlist[ticker.upper()]["alerts"]) == 0:
        db_client.delete_ticker_db(ticker.upper())

    return True


def update_watchlist_alert(db_client: Any, payload: UpdateAlertRequest) -> bool:
    symbol = payload.ticker.upper()
    watchlist = db_client.get_watchlist()
    if symbol in watchlist:
        for alert in watchlist[symbol]["alerts"]:
            if alert["metric"] == payload.metric.lower():
                db_client.update_alert_target(alert["id"], payload.value)
                return True
    return False
