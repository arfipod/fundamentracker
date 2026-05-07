from __future__ import annotations

from typing import Any

from market_data.metric_definitions import is_supported_metric
from market_data.normalizers import normalize_metric_value, normalize_symbol
from market_data.providers.base import MarketDataProvider
from market_data.providers.yfinance_provider import YFinanceProvider


class MarketDataService:
    def __init__(self, provider: MarketDataProvider | None = None):
        self.provider = provider or YFinanceProvider()

    def get_quote(self, symbol: str) -> dict[str, Any]:
        return self.provider.get_quote(normalize_symbol(symbol))

    def get_metric(self, symbol: str, metric: str, *, normalized: bool = True) -> float | None:
        metric = metric.lower()
        if not is_supported_metric(metric):
            raise ValueError(f"Invalid metric: {metric}")
        value = self.provider.get_metric(normalize_symbol(symbol), metric)
        if value is None:
            return None
        if not normalized:
            return value
        return normalize_metric_value(metric, value)

    def get_price_history(self, symbol: str, period: str) -> list[dict[str, float | str]]:
        if hasattr(self.provider, "price_history_points"):
            return self.provider.price_history_points(normalize_symbol(symbol), period)

        history = self.provider.get_price_history(normalize_symbol(symbol), period)
        from market_data.normalizers import price_history_points

        return price_history_points(history)

    def get_metric_history(self, symbol: str, metric: str, period: str) -> list[dict[str, float | str]]:
        metric = metric.lower()
        if not is_supported_metric(metric):
            raise ValueError("Unsupported metric for history")
        return self.provider.get_metric_history(normalize_symbol(symbol), metric, period)

    def search_symbols(self, query: str) -> list[dict[str, str | None]]:
        if not query.strip():
            return []
        return self.provider.search_symbols(query.strip())


_market_data_service: MarketDataService | None = None


def get_market_data_service() -> MarketDataService:
    global _market_data_service
    if _market_data_service is None:
        _market_data_service = MarketDataService()
    return _market_data_service
