from __future__ import annotations

from typing import Any, Callable

from schemas.alerts import AddAlertRequest, UpdateAlertRequest
from schemas.watchlist import AddTickerTagRequest, WatchlistMetadataRequest


class WatchlistValidationError(ValueError):
    pass


class WatchlistAlertNotFoundError(ValueError):
    pass


class WatchlistAmbiguousAlertError(ValueError):
    pass


def get_watchlist(db_client: Any):
    return db_client.get_watchlist()


def get_tags(db_client: Any):
    return db_client.get_tags()


def _require_ticker_exists(db_client: Any, symbol: str) -> None:
    if symbol not in db_client.get_watchlist():
        raise WatchlistAlertNotFoundError("Ticker not found")


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip()


def update_ticker_metadata(
    db_client: Any,
    ticker: str,
    payload: WatchlistMetadataRequest,
) -> dict[str, Any]:
    symbol = ticker.upper()
    metadata = {}
    payload_data = (
        payload.model_dump(exclude_unset=True)
        if hasattr(payload, "model_dump")
        else payload.dict(exclude_unset=True)
    )
    for key, value in payload_data.items():
        clean_value = _clean_text(value)
        if clean_value is not None:
            metadata[key] = clean_value
    result = db_client.update_ticker_metadata(symbol, metadata)
    if result is None:
        raise WatchlistAlertNotFoundError("Ticker not found")
    return result


def add_ticker_tag(
    db_client: Any,
    ticker: str,
    payload: AddTickerTagRequest,
) -> dict[str, Any]:
    symbol = ticker.upper()
    _require_ticker_exists(db_client, symbol)

    name = payload.name.strip().lower()
    if not name:
        raise WatchlistValidationError("Tag name is required")

    color = _clean_text(payload.color)
    result = db_client.add_tag_to_ticker(symbol, name, color)
    if result is None:
        raise WatchlistValidationError("Unable to add tag")
    return result


def remove_ticker_tag(db_client: Any, ticker: str, tag_name_or_id: str) -> bool:
    symbol = ticker.upper()
    _require_ticker_exists(db_client, symbol)
    identifier = tag_name_or_id.strip().lower()
    if not identifier:
        raise WatchlistValidationError("Tag name or ID is required")
    return bool(db_client.remove_tag_from_ticker(symbol, identifier))


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
