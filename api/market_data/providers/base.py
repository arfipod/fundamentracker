from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import pandas as pd


class MarketDataProvider(ABC):
    source: str

    @abstractmethod
    def get_quote(self, symbol: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def get_metric(self, symbol: str, metric: str) -> float | None:
        raise NotImplementedError

    @abstractmethod
    def get_price_history(self, symbol: str, period: str) -> pd.DataFrame:
        raise NotImplementedError

    @abstractmethod
    def get_metric_history(self, symbol: str, metric: str, period: str) -> list[dict[str, float | str]]:
        raise NotImplementedError

    @abstractmethod
    def search_symbols(self, query: str) -> list[dict[str, str | None]]:
        raise NotImplementedError
