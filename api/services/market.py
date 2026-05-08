from __future__ import annotations

import logging
from typing import Any

from market_data.metric_definitions import get_metric_catalog


DEFAULT_MARKET_OVERVIEW_TICKERS = ["SPY", "QQQ", "DIA"]
logger = logging.getLogger(__name__)


def _provider_source(market_data_service: Any) -> str | None:
    provider = getattr(market_data_service, "provider", None)
    if provider is None:
        return None
    return getattr(provider, "source", provider.__class__.__name__)


def search_symbols(market_data_service: Any, query: str):
    return market_data_service.search_symbols(query)


def get_provider_health(market_data_service: Any):
    return market_data_service.get_provider_health()


def get_metrics_catalog() -> list[dict[str, Any]]:
    return get_metric_catalog()


def get_metric_current(
    market_data_service: Any,
    *,
    ticker: str,
    metric: str,
    metrics_map: dict[str, Any],
) -> dict[str, Any]:
    metric_name = metric.lower()
    if metric_name not in metrics_map:
        raise ValueError(f"Unsupported metric: {metric_name}")

    snapshot = market_data_service.get_metric_snapshot(ticker.upper(), metric_name)
    return {
        "ticker": ticker.upper(),
        "metric": metric_name,
        "value": snapshot.get("value"),
        "stale": snapshot.get("stale", False),
        "source": snapshot.get("source"),
        "as_of_date": snapshot.get("as_of_date"),
        "fetched_at": snapshot.get("fetched_at"),
        "expires_at": snapshot.get("expires_at"),
        "confidence": snapshot.get("confidence"),
    }


def get_history(market_data_service: Any, *, ticker: str, metric: str, period: str = "1y"):
    return market_data_service.get_metric_history(ticker.upper(), metric, period)


def get_market_overview(
    market_data_service: Any,
    *,
    tickers: list[str] | None = None,
) -> list[dict[str, float | str]]:
    overview = []
    for ticker in tickers or DEFAULT_MARKET_OVERVIEW_TICKERS:
        try:
            history = market_data_service.get_price_history(ticker, "2d")
            values = [point["value"] for point in history if point.get("value") is not None]
            if len(values) >= 2:
                current = values[-1]
                previous = values[-2]
                change = ((current - previous) / previous) * 100
                overview.append(
                    {
                        "symbol": ticker,
                        "current": float(current),
                        "change_percent": float(change),
                    }
                )
            elif len(values) == 1:
                overview.append(
                    {
                        "symbol": ticker,
                        "current": float(values[-1]),
                        "change_percent": 0.0,
                    }
                )
        except Exception as error:
            logger.warning(
                "Failed to fetch market overview price history",
                extra={
                    "ticker": ticker,
                    "metric": "price_history",
                    "provider": _provider_source(market_data_service),
                },
                exc_info=error,
            )
    return overview
