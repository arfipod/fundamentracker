from __future__ import annotations

import time
from typing import Any

import pandas as pd
import requests
import yfinance as yf

from market_data.metric_definitions import get_metric_definition
from market_data.normalizers import (
    calculate_historical_fundamental,
    normalize_history_points,
    normalize_metric_value,
    normalize_symbol,
    price_history_points,
    to_float,
)
from market_data.providers.base import MarketDataProvider


class YFinanceProvider(MarketDataProvider):
    source = "yfinance"

    def __init__(self, cache_ttl_seconds: int = 120, requests_client=requests):
        self.cache_ttl_seconds = cache_ttl_seconds
        self.requests_client = requests_client
        self._quote_cache: dict[str, tuple[float, dict[str, Any]]] = {}

    def get_quote(self, symbol: str) -> dict[str, Any]:
        symbol = normalize_symbol(symbol)
        info = dict(self._get_ticker_info(symbol))
        info.setdefault("symbol", symbol)
        info.setdefault("name", info.get("shortName") or info.get("longName") or symbol)
        info.setdefault("price", info.get("currentPrice") or info.get("regularMarketPrice"))
        info.setdefault("source", self.source)
        return info

    def get_metric(self, symbol: str, metric: str) -> float | None:
        symbol = normalize_symbol(symbol)
        metric = metric.lower()
        definition = get_metric_definition(metric)
        info = self._get_ticker_info(symbol)
        value = to_float(info.get(definition.yf_key))
        if value is not None:
            return value

        if metric == "roic":
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="5d")
            if hist.empty:
                return None
            series = calculate_historical_fundamental(
                self._safe_statement(ticker, "quarterly_incomestmt"),
                self._safe_statement(ticker, "quarterly_balancesheet"),
                metric,
                hist.index,
            )
            return to_float(series.dropna().iloc[-1]) if not series.dropna().empty else None

        return None

    def get_price_history(self, symbol: str, period: str) -> pd.DataFrame:
        symbol = normalize_symbol(symbol)
        return yf.Ticker(symbol).history(period=period)

    def get_metric_history(self, symbol: str, metric: str, period: str) -> list[dict[str, float | str]]:
        symbol = normalize_symbol(symbol)
        metric = metric.lower()
        hist = self.get_price_history(symbol, period)
        if hist.empty:
            return []

        if metric == "price":
            return price_history_points(hist)

        info = self._get_ticker_info(symbol)

        if metric == "pe":
            eps = to_float(info.get("trailingEps"))
            if eps in (None, 0):
                raise ValueError("No valid EPS data for PE calculation")
            return self._ratio_history(hist, eps)

        if metric == "fpe":
            forward_eps = to_float(info.get("forwardEps"))
            if forward_eps in (None, 0):
                raise ValueError("No valid forward EPS data")
            return self._ratio_history(hist, forward_eps)

        if metric == "pb":
            book_value = to_float(info.get("bookValue"))
            if book_value in (None, 0):
                raise ValueError("No valid book value data")
            return self._ratio_history(hist, book_value)

        if metric == "evebitda":
            shares = to_float(info.get("sharesOutstanding"))
            debt = to_float(info.get("totalDebt")) or 0
            cash = to_float(info.get("totalCash")) or 0
            ebitda = to_float(info.get("ebitda"))
            if not shares or not ebitda:
                raise ValueError("No valid data for EV/EBITDA calculation")

            net_debt = debt - cash
            data: list[dict[str, float | str]] = []
            for date, row in hist.iterrows():
                close = to_float(row.get("Close"))
                if close is None:
                    continue
                enterprise_value = close * shares + net_debt
                data.append({"date": pd.Timestamp(date).strftime("%Y-%m-%d"), "value": enterprise_value / ebitda})
            return data

        if metric in {"roe", "roic", "debttoequity", "profitmargins", "operatingmargins"}:
            ticker = yf.Ticker(symbol)
            fund_series = calculate_historical_fundamental(
                self._safe_statement(ticker, "quarterly_incomestmt"),
                self._safe_statement(ticker, "quarterly_balancesheet"),
                metric,
                hist.index,
            )
            if fund_series.isna().all():
                current_val = self.get_metric(symbol, metric)
                if current_val is None:
                    raise ValueError(f"No {metric.upper()} data available")
                return [
                    {"date": pd.Timestamp(date).strftime("%Y-%m-%d"), "value": normalize_metric_value(metric, current_val)}
                    for date in hist.index
                ]
            return normalize_history_points(fund_series, metric)

        if metric == "dividendyield":
            dividend = to_float(info.get("trailingAnnualDividendRate")) or to_float(info.get("dividendRate"))
            if not dividend:
                raise ValueError("No dividend data available")
            data = []
            for date, row in hist.iterrows():
                close = to_float(row.get("Close"))
                if close is None or close == 0:
                    continue
                data.append({"date": pd.Timestamp(date).strftime("%Y-%m-%d"), "value": (dividend / close) * 100})
            return data

        if metric == "payoutratio":
            payout_ratio = to_float(info.get("payoutRatio"))
            if payout_ratio is None:
                raise ValueError("No payout ratio data available")
            return [
                {"date": pd.Timestamp(date).strftime("%Y-%m-%d"), "value": payout_ratio * 100}
                for date in hist.index
            ]

        raise ValueError("Unsupported metric for history")

    def search_symbols(self, query: str) -> list[dict[str, str | None]]:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = self.requests_client.get(
            "https://query2.finance.yahoo.com/v1/finance/search",
            params={"q": query, "quotesCount": 5},
            headers=headers,
            timeout=5,
        )
        if not response.ok:
            return []

        data = response.json()
        quotes = data.get("quotes", [])
        allowed_quote_types = {"EQUITY", "ETF", "CURRENCY", "CRYPTOCURRENCY"}
        return [
            {
                "symbol": quote.get("symbol"),
                "name": quote.get("shortname", quote.get("longname", "")),
            }
            for quote in quotes
            if "symbol" in quote and quote.get("quoteType") in allowed_quote_types
        ]

    def price_history_points(self, symbol: str, period: str) -> list[dict[str, float | str]]:
        return price_history_points(self.get_price_history(symbol, period))

    def _get_ticker_info(self, symbol: str) -> dict[str, Any]:
        now = time.time()
        symbol = normalize_symbol(symbol)

        if symbol in self._quote_cache:
            cached_time, data = self._quote_cache[symbol]
            if now - cached_time < self.cache_ttl_seconds:
                return data

        data = yf.Ticker(symbol).info
        if not isinstance(data, dict):
            data = {}
        self._quote_cache[symbol] = (now, data)
        return data

    @staticmethod
    def _safe_statement(ticker, attribute: str) -> pd.DataFrame:
        try:
            statement = getattr(ticker, attribute)
            return statement if statement is not None else pd.DataFrame()
        except Exception:
            return pd.DataFrame()

    @staticmethod
    def _ratio_history(history: pd.DataFrame, denominator: float) -> list[dict[str, float | str]]:
        data: list[dict[str, float | str]] = []
        for date, row in history.iterrows():
            close = to_float(row.get("Close"))
            if close is None:
                continue
            data.append({"date": pd.Timestamp(date).strftime("%Y-%m-%d"), "value": close / denominator})
        return data
