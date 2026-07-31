from __future__ import annotations

from datetime import date
import time
from typing import Any

import pandas as pd
import requests
import yfinance as yf

from market_data.derived_metrics import (
    FundamentalDataPack,
    VALUATION_LABELS,
    calculate_derived_metric,
    calculate_eps_revision_90d,
    calculate_eps_revision_balance,
    calculate_valuation_context_metric,
    valuation_frequency_for_period,
    valuation_history_points,
)
from market_data.metric_definitions import get_metric_definition
from market_data.normalizers import (
    calculate_historical_fundamental,
    normalize_history_points,
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
        self._ticker_cache: dict[str, Any] = {}
        self._fundamental_cache: dict[str, tuple[float, FundamentalDataPack]] = {}
        self._valuation_cache: dict[tuple[str, str], tuple[float, pd.DataFrame]] = {}

    def get_quote(self, symbol: str) -> dict[str, Any]:
        symbol = normalize_symbol(symbol)
        info = dict(self._get_ticker_info(symbol))
        fast_info = self._get_fast_info(symbol)

        price = (
            to_float(fast_info.get("last_price"))
            or to_float(fast_info.get("lastPrice"))
            or to_float(info.get("currentPrice"))
            or to_float(info.get("regularMarketPrice"))
        )
        market_cap = (
            to_float(fast_info.get("market_cap"))
            or to_float(fast_info.get("marketCap"))
            or to_float(info.get("marketCap"))
        )
        shares = to_float(fast_info.get("shares")) or to_float(info.get("sharesOutstanding"))

        info.setdefault("symbol", symbol)
        info.setdefault("name", info.get("shortName") or info.get("longName") or symbol)
        info["price"] = price
        if price is not None:
            info.setdefault("currentPrice", price)
        if market_cap is not None:
            info["marketCap"] = market_cap
        if shares is not None:
            info["sharesOutstanding"] = shares
        info.setdefault("currency", fast_info.get("currency"))
        info.setdefault("source", self.source)
        return info

    def get_metric(self, symbol: str, metric: str) -> float | None:
        observation = self.get_metric_observation(symbol, metric)
        return to_float(observation.get("value")) if observation else None

    def get_metric_observation(self, symbol: str, metric: str) -> dict[str, Any] | None:
        symbol = normalize_symbol(symbol)
        metric = metric.lower()
        definition = get_metric_definition(metric)
        info = self._get_ticker_info(symbol)

        if metric == "price":
            fast_info = self._get_fast_info(symbol)
            value = (
                to_float(fast_info.get("last_price"))
                or to_float(fast_info.get("lastPrice"))
                or to_float(info.get("currentPrice"))
                or to_float(info.get("regularMarketPrice"))
            )
            return self._observation(value, source_detail="fast_info.last_price", confidence=0.9)

        if metric == "market_cap":
            fast_info = self._get_fast_info(symbol)
            value = (
                to_float(fast_info.get("market_cap"))
                or to_float(fast_info.get("marketCap"))
                or to_float(info.get("marketCap"))
                or self._current_valuation_value(symbol, metric)
            )
            return self._observation(value, source_detail="fast_info.market_cap", confidence=0.85)

        if metric == "enterprise_value":
            value = to_float(info.get("enterpriseValue")) or self._current_valuation_value(symbol, metric)
            if value is None:
                derived_pack = self._get_fundamental_pack(symbol)
                market_cap = self._market_cap_from_pack(derived_pack)
                debt = self._latest_statement_value(derived_pack.quarterly_balance, "Total Debt") or 0.0
                cash = self._latest_statement_value(
                    derived_pack.quarterly_balance,
                    "Cash Cash Equivalents And Short Term Investments",
                    "Cash And Cash Equivalents",
                ) or 0.0
                value = market_cap + debt - cash if market_cap is not None else None
            return self._observation(value, source_detail="enterprise value", confidence=0.8)

        if definition.source_kind == "statement":
            result = calculate_derived_metric(metric, self._get_fundamental_pack(symbol))
            if result is not None:
                return self._observation(
                    result.value,
                    as_of_date=result.as_of_date,
                    source_detail=result.source_detail,
                    period=result.period,
                    formula_version=result.formula_version,
                    confidence=0.75,
                )
            if definition.yf_key:
                return self._observation(
                    to_float(info.get(definition.yf_key)),
                    source_detail=f"info.{definition.yf_key}",
                    confidence=0.65,
                )
            return None

        if definition.source_kind == "growth":
            direct = to_float(info.get(definition.yf_key)) if definition.yf_key else None
            if direct is not None:
                return self._observation(
                    direct,
                    source_detail=f"info.{definition.yf_key}",
                    period="YoY",
                    confidence=0.75,
                )
            result = calculate_derived_metric(metric, self._get_fundamental_pack(symbol))
            if result is None:
                return None
            return self._observation(
                result.value,
                as_of_date=result.as_of_date,
                source_detail=result.source_detail,
                period=result.period,
                formula_version=result.formula_version,
                confidence=0.7,
            )

        if definition.source_kind == "valuation_context":
            valuation = self._get_valuation_measures(symbol, "quarterly")
            result = calculate_valuation_context_metric(metric, valuation)
            if result is None:
                return None
            return self._observation(
                result.value,
                as_of_date=result.as_of_date,
                source_detail=result.source_detail,
                period=result.period,
                formula_version=result.formula_version,
                confidence=0.75,
            )

        if definition.source_kind == "analyst":
            ticker = self._get_ticker(symbol)
            if metric == "eps_revision_90d":
                result = calculate_eps_revision_90d(self._safe_dataframe_attr(ticker, "eps_trend"))
            else:
                result = calculate_eps_revision_balance(self._safe_dataframe_attr(ticker, "eps_revisions"))
            if result is None:
                return None
            return self._observation(
                result.value,
                as_of_date=result.as_of_date,
                source_detail=result.source_detail,
                period=result.period,
                formula_version=result.formula_version,
                confidence=0.6,
            )

        value = to_float(info.get(definition.yf_key)) if definition.yf_key else None
        if value is None and metric in VALUATION_LABELS:
            value = self._current_valuation_value(symbol, metric)
        return self._observation(
            value,
            source_detail=f"info.{definition.yf_key}" if definition.yf_key else "valuation measures",
            confidence=0.8,
        )

    def get_price_history(self, symbol: str, period: str) -> pd.DataFrame:
        symbol = normalize_symbol(symbol)
        return self._get_ticker(symbol).history(period=period)

    def get_metric_history(self, symbol: str, metric: str, period: str) -> list[dict[str, float | str]]:
        symbol = normalize_symbol(symbol)
        metric = metric.lower()

        if metric == "price":
            history = self.get_price_history(symbol, period)
            return price_history_points(history)

        if metric in VALUATION_LABELS:
            frequency = valuation_frequency_for_period(period)
            valuation = self._get_valuation_measures(symbol, frequency)
            points = valuation_history_points(valuation, metric, period)
            if not points:
                raise ValueError(f"No real historical {metric.upper()} valuation data available")
            return points

        if metric in {"roe", "roic", "debttoequity", "profitmargins", "operatingmargins"}:
            history = self.get_price_history(symbol, period)
            if history.empty:
                return []
            ticker = self._get_ticker(symbol)
            fundamental_series = calculate_historical_fundamental(
                self._safe_statement(ticker, "quarterly_incomestmt"),
                self._safe_statement(ticker, "quarterly_balancesheet"),
                metric,
                history.index,
            )
            if fundamental_series.isna().all():
                raise ValueError(f"No real historical {metric.upper()} statement data available")
            return normalize_history_points(fundamental_series, metric)

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

    def _get_ticker(self, symbol: str):
        symbol = normalize_symbol(symbol)
        ticker = self._ticker_cache.get(symbol)
        if ticker is None:
            ticker = yf.Ticker(symbol)
            self._ticker_cache[symbol] = ticker
        return ticker

    def _get_ticker_info(self, symbol: str) -> dict[str, Any]:
        now = time.time()
        symbol = normalize_symbol(symbol)

        if symbol in self._quote_cache:
            cached_time, data = self._quote_cache[symbol]
            if now - cached_time < self.cache_ttl_seconds:
                return data

        data = self._safe_mapping_attr(self._get_ticker(symbol), "info")
        self._quote_cache[symbol] = (now, data)
        return data

    def _get_fast_info(self, symbol: str) -> dict[str, Any]:
        ticker = self._get_ticker(symbol)
        try:
            fast_info = ticker.fast_info
        except Exception:
            return {}

        result: dict[str, Any] = {}
        for key in (
            "last_price",
            "lastPrice",
            "market_cap",
            "marketCap",
            "shares",
            "currency",
            "exchange",
            "timezone",
        ):
            try:
                value = fast_info.get(key)
            except Exception:
                value = None
            if value is not None:
                result[key] = value
        return result

    def _get_fundamental_pack(self, symbol: str) -> FundamentalDataPack:
        now = time.time()
        symbol = normalize_symbol(symbol)
        cached = self._fundamental_cache.get(symbol)
        cache_ttl = max(self.cache_ttl_seconds, 300)
        if cached and now - cached[0] < cache_ttl:
            return cached[1]

        ticker = self._get_ticker(symbol)
        pack = FundamentalDataPack(
            info=dict(self._get_ticker_info(symbol)),
            fast_info=self._get_fast_info(symbol),
            ttm_income=self._safe_statement(ticker, "ttm_income_stmt"),
            ttm_cash_flow=self._safe_statement(ticker, "ttm_cash_flow"),
            quarterly_balance=self._safe_statement(ticker, "quarterly_balance_sheet", "quarterly_balancesheet"),
            annual_income=self._safe_statement(ticker, "income_stmt", "incomestmt"),
            annual_cash_flow=self._safe_statement(ticker, "cash_flow", "cashflow"),
            annual_balance=self._safe_statement(ticker, "balance_sheet", "balancesheet"),
        )
        self._fundamental_cache[symbol] = (now, pack)
        return pack

    def _get_valuation_measures(self, symbol: str, frequency: str) -> pd.DataFrame:
        now = time.time()
        key = (normalize_symbol(symbol), frequency)
        cached = self._valuation_cache.get(key)
        cache_ttl = max(self.cache_ttl_seconds, 300)
        if cached and now - cached[0] < cache_ttl:
            return cached[1]

        ticker = self._get_ticker(symbol)
        try:
            valuation = ticker.get_valuation_measures(freq=frequency, periods=None)
        except Exception:
            valuation = pd.DataFrame()
        if valuation is None:
            valuation = pd.DataFrame()
        self._valuation_cache[key] = (now, valuation)
        return valuation

    def _current_valuation_value(self, symbol: str, metric: str) -> float | None:
        label = VALUATION_LABELS.get(metric)
        if label is None:
            return None
        valuation = self._get_valuation_measures(symbol, "quarterly")
        if valuation.empty or label not in valuation.index or "Current" not in valuation.columns:
            return None
        row = valuation.loc[label]
        if isinstance(row, pd.DataFrame):
            row = row.iloc[0]
        return to_float(row.get("Current"))

    @staticmethod
    def _safe_mapping_attr(ticker, attribute: str) -> dict[str, Any]:
        try:
            value = getattr(ticker, attribute)
        except Exception:
            return {}
        return dict(value) if isinstance(value, dict) else {}

    @staticmethod
    def _safe_dataframe_attr(ticker, attribute: str) -> pd.DataFrame:
        try:
            value = getattr(ticker, attribute)
        except Exception:
            return pd.DataFrame()
        return value if isinstance(value, pd.DataFrame) else pd.DataFrame()

    @staticmethod
    def _safe_statement(ticker, *attributes: str) -> pd.DataFrame:
        for attribute in attributes:
            try:
                statement = getattr(ticker, attribute)
            except Exception:
                continue
            if isinstance(statement, pd.DataFrame) and not statement.empty:
                return statement
        return pd.DataFrame()

    @staticmethod
    def _latest_statement_value(statement: pd.DataFrame, *aliases: str) -> float | None:
        if statement is None or statement.empty:
            return None
        normalized_aliases = {"".join(character for character in alias.lower() if character.isalnum()) for alias in aliases}
        label = next(
            (
                index
                for index in statement.index
                if "".join(character for character in str(index).lower() if character.isalnum()) in normalized_aliases
            ),
            None,
        )
        if label is None:
            return None
        row = pd.to_numeric(statement.loc[label], errors="coerce").dropna()
        return to_float(row.iloc[0]) if not row.empty else None

    @staticmethod
    def _market_cap_from_pack(pack: FundamentalDataPack) -> float | None:
        value = (
            to_float(pack.fast_info.get("market_cap"))
            or to_float(pack.fast_info.get("marketCap"))
            or to_float(pack.info.get("marketCap"))
        )
        if value is not None:
            return value
        price = to_float(pack.fast_info.get("last_price")) or to_float(pack.info.get("currentPrice"))
        shares = to_float(pack.fast_info.get("shares")) or to_float(pack.info.get("sharesOutstanding"))
        return price * shares if price is not None and shares is not None else None

    @staticmethod
    def _observation(
        value: Any,
        *,
        as_of_date: date | None = None,
        source_detail: str,
        period: str | None = None,
        formula_version: str | None = None,
        confidence: float,
    ) -> dict[str, Any] | None:
        numeric = to_float(value)
        if numeric is None:
            return None
        return {
            "value": numeric,
            "as_of_date": as_of_date,
            "source_detail": source_detail,
            "period": period,
            "formula_version": formula_version,
            "confidence": confidence,
        }
