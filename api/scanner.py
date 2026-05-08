import logging

from alert_evaluator import calculate_relative_diff, evaluate_alert
from market_data.service import MarketDataService, get_market_data_service
from repositories.factory import get_repository

logger = logging.getLogger(__name__)


def _provider_source(market_data: MarketDataService) -> str | None:
    provider = getattr(market_data, "provider", None)
    if provider is None:
        return None
    return getattr(provider, "source", provider.__class__.__name__)


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
                
            try:
                current_val = market_data.get_metric(ticker, alert["metric"])
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
            db.update_alert_status(alert["id"], is_triggered, current_val)
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
                        "source": _provider_source(market_data),
                        "message": msg,
                    },
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
