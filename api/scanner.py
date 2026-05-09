import logging
from typing import Any

from alert_evaluator import calculate_relative_diff, evaluate_alert
from market_data.service import MarketDataService, get_market_data_service
from repositories.factory import get_repository

logger = logging.getLogger(__name__)


def _provider_source(market_data: MarketDataService) -> str | None:
    provider = getattr(market_data, "provider", None)
    if provider is None:
        return None
    return getattr(provider, "source", provider.__class__.__name__)


def _snapshot_metadata(snapshot: dict[str, Any] | None) -> dict[str, Any]:
    if not snapshot:
        return {}
    return {
        "source": snapshot.get("source"),
        "as_of_date": snapshot.get("as_of_date"),
        "fetched_at": snapshot.get("fetched_at"),
        "expires_at": snapshot.get("expires_at"),
        "stale": snapshot.get("stale", False),
        "confidence": snapshot.get("confidence"),
    }


def _signal_title(ticker: str, metric: str, operator: str, target: Any) -> str:
    direction = {
        "<": "crossed below",
        "<=": "crossed at or below",
        ">": "crossed above",
        ">=": "crossed at or above",
        "==": "matched",
        "=": "matched",
    }.get(operator, operator)
    return f"{ticker} {metric.upper()} {direction} {target}"


def _alert_signal_severity(alert: dict[str, Any]) -> str:
    metric = str(alert.get("metric") or "").lower()
    operator = alert.get("operator")
    if metric in {"price", "market_cap"} and operator in {"<", "<="}:
        return "critical"
    return "warning"


def run_fundamental_scan(
    send_alert_func,
    market_data_service: MarketDataService | None = None,
    repository=None,
):
    """
    1) Fetches watchlist from db
    2) Performs logic for each alert
    3) Triggers log & updates if condition met
    """
    market_data = market_data_service or get_market_data_service()
    db = repository or get_repository()
    watchlist = db.get_watchlist()
    
    symbols = list(watchlist.keys())
    if not symbols:
        logger.info("Scan skipped because watchlist is empty")
        return
    logger.info("Scan started", extra={"ticker_count": len(symbols)})
        
    for ticker, details in list(watchlist.items()):
        
        for alert in details.get("alerts", []):
            if not alert.get("is_active", True):
                # Always update the status as False if not active to avoid ghost states? Or just leave it. 
                # Better left as is.
                continue
                
            metric_snapshot = None
            try:
                metric_snapshot = market_data.get_metric_snapshot(ticker, alert["metric"])
                current_val = metric_snapshot.get("value")
            except Exception as error:
                logger.warning(
                    "Failed to fetch metric for alert",
                    extra={
                        "ticker": ticker,
                        "alert_id": alert.get("id"),
                        "metric": alert.get("metric"),
                        "provider": _provider_source(market_data),
                    },
                    exc_info=error,
                )
                current_val = None
            current_metadata = _snapshot_metadata(metric_snapshot)
            if current_val is None:
                logger.info(
                    "Skipping alert because current metric value is missing",
                    extra={
                        "ticker": ticker,
                        "alert_id": alert.get("id"),
                        "metric": alert.get("metric"),
                        "provider": _provider_source(market_data),
                    },
                )
                continue
                
            is_triggered = evaluate_alert(
                current_val,
                alert["target"],
                alert["operator"],
                alert.get("alert_type"),
                alert.get("reference_value"),
            )
                
            # Update DB with new value and trigger state
            db.update_alert_status(alert["id"], is_triggered, current_val, current_metadata)
            logger.info(
                "Alert evaluated",
                extra={
                    "ticker": ticker,
                    "alert_id": alert.get("id"),
                    "metric": alert.get("metric"),
                    "is_triggered": is_triggered,
                    "current_value": current_val,
                },
            )
            
            # If crossed from untriggered to triggered
            if is_triggered and not alert.get("is_triggered", False):
                # Format message
                if alert.get("alert_type") == "relative":
                    diff = calculate_relative_diff(current_val, alert.get("reference_value"))
                    diff_msg = f", Diff: {diff:.2f}%" if diff is not None else ""
                    msg = f"🚨 *{details['name']}* ({ticker}): {alert['metric'].upper()} changed by {alert['operator']} {alert['target']}% (Current: {current_val:.2f}, Ref: {alert['reference_value']:.2f}{diff_msg})"
                else:
                    msg = f"🚨 *{details['name']}* ({ticker}): {alert['metric'].upper()} {alert['operator']} {alert['target']} (Current: {current_val:.2f})"

                # Triggered! Log to history with denormalized alert context.
                db.log_alert_history(
                    alert["id"],
                    current_val,
                    alert["target"],
                    {
                        "ticker_symbol": ticker,
                        "company_name": details.get("name"),
                        "metric": alert.get("metric"),
                        "operator": alert.get("operator"),
                        "alert_type": alert.get("alert_type") or "absolute",
                        "reference_value": alert.get("reference_value"),
                        "current_value": current_val,
                        "source": current_metadata.get("source") or _provider_source(market_data),
                        "as_of_date": current_metadata.get("as_of_date"),
                        "fetched_at": current_metadata.get("fetched_at"),
                        "message": msg,
                    },
                )
                db.create_signal(
                    {
                        "ticker_symbol": ticker,
                        "company_name": details.get("name"),
                        "signal_type": "alert_triggered",
                        "severity": _alert_signal_severity(alert),
                        "title": _signal_title(
                            ticker,
                            alert.get("metric", ""),
                            alert.get("operator", ""),
                            alert.get("target"),
                        ),
                        "message": msg,
                        "metric": alert.get("metric"),
                        "current_value": current_val,
                        "previous_value": alert.get("current_value"),
                        "target_value": alert.get("target"),
                        "source": current_metadata.get("source") or _provider_source(market_data),
                        "as_of_date": current_metadata.get("as_of_date"),
                        "fetched_at": current_metadata.get("fetched_at"),
                        "raw_payload": {
                            "alert_id": alert.get("id"),
                            "operator": alert.get("operator"),
                            "alert_type": alert.get("alert_type") or "absolute",
                            "reference_value": alert.get("reference_value"),
                            "current_metadata": current_metadata,
                        },
                    }
                )
                logger.info(
                    "Alert triggered",
                    extra={
                        "ticker": ticker,
                        "alert_id": alert.get("id"),
                        "metric": alert.get("metric"),
                        "current_value": current_val,
                        "target_value": alert.get("target"),
                    },
                )
                    
                send_alert_func(msg)
