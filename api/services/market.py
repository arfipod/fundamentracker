from __future__ import annotations

from typing import Any


DEFAULT_MARKET_OVERVIEW_TICKERS = ["SPY", "QQQ", "DIA"]


def search_symbols(market_data_service: Any, query: str):
    return market_data_service.search_symbols(query)


def get_provider_health(market_data_service: Any):
    return market_data_service.get_provider_health()


def get_metric_current(
    market_data_service: Any,
    *,
    ticker: str,
    metric: str,
    metrics_map: dict[str, Any],
) -> dict[str, Any]:
    metric_name = metric.lower()
    service_metric = metric_name if metric_name in metrics_map else "price"
    snapshot = market_data_service.get_metric_snapshot(ticker.upper(), service_metric)
    return {
        "ticker": ticker.upper(),
        "metric": metric,
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
            print(f"Error fetching {ticker}: {error}")
    return overview
