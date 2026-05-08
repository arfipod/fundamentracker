from __future__ import annotations

from typing import Any, Callable

from schemas.alerts import AddAlertRequest, UpdateAlertRequest


class WatchlistValidationError(ValueError):
    pass


class WatchlistAlertNotFoundError(ValueError):
    pass


class WatchlistAmbiguousAlertError(ValueError):
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


def _find_single_alert_by_symbol_metric(db_client: Any, ticker: str, metric: str) -> tuple[str, dict[str, Any]]:
    symbol = ticker.upper()
    metric_name = metric.lower()
    watchlist = db_client.get_watchlist()
    alerts = [
        alert
        for alert in watchlist.get(symbol, {}).get("alerts", [])
        if str(alert.get("metric", "")).lower() == metric_name
    ]

    if not alerts:
        raise WatchlistAlertNotFoundError("Alert not found")
    if len(alerts) > 1:
        raise WatchlistAmbiguousAlertError(
            "Multiple alerts match this ticker and metric; use /alerts/{alert_id}"
        )

    return symbol, alerts[0]


def remove_watchlist_alert(db_client: Any, ticker: str, metric: str) -> bool:
    _, alert = _find_single_alert_by_symbol_metric(db_client, ticker, metric)
    deleted = db_client.delete_alert_db(alert_id=alert["id"])
    if not deleted:
        return False

    return True


def update_watchlist_alert(db_client: Any, payload: UpdateAlertRequest) -> bool:
    _, alert = _find_single_alert_by_symbol_metric(db_client, payload.ticker, payload.metric)
    return bool(db_client.update_alert_target(alert["id"], payload.value))
