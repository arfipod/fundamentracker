from __future__ import annotations

import logging
import math
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from db import client as db
from market_data.metric_definitions import get_metric_definition, is_supported_metric
from market_data.normalizers import normalize_metric_value, normalize_symbol, to_float
from market_data.providers.base import MarketDataProvider
from market_data.providers.yfinance_provider import YFinanceProvider

logger = logging.getLogger(__name__)
DEFAULT_PROVIDER_CONFIDENCE = 0.8


class MarketDataService:
    def __init__(
        self,
        provider: MarketDataProvider | None = None,
        *,
        snapshot_repository: Any | None = None,
        ttl_seconds: dict[str, int] | None = None,
        clock: Any | None = None,
    ):
        from config import get_market_data_ttls

        self.provider = provider or YFinanceProvider()
        self.snapshot_repository = snapshot_repository or db
        self.ttl_seconds = get_market_data_ttls()
        if ttl_seconds:
            self.ttl_seconds.update(ttl_seconds)
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def get_quote(self, symbol: str) -> dict[str, Any]:
        symbol = normalize_symbol(symbol)
        now = self._now()
        fresh = self._get_fresh_snapshot(symbol, "quote", now)
        if fresh:
            return self._quote_from_snapshot(fresh)

        try:
            quote = self.provider.get_quote(symbol)
            self._record_provider_ok(now)
        except Exception as error:
            self._record_provider_error(error, now, symbol=symbol, metric="quote")
            stale = self._get_latest_snapshot(symbol, "quote")
            if stale:
                stale["stale"] = True
                return self._quote_from_snapshot(stale)
            raise

        price = to_float(quote.get("price") or quote.get("currentPrice") or quote.get("regularMarketPrice"))
        snapshot = self._save_snapshot(
            {
                "symbol": symbol,
                "metric": "quote",
                "value": price,
                "unit": "currency",
                "currency": quote.get("currency"),
                "source": self._provider_source(),
                "as_of_date": self._quote_as_of_date(quote),
                "fetched_at": now,
                "expires_at": self._expires_at(now, "quote"),
                "confidence": DEFAULT_PROVIDER_CONFIDENCE,
                "raw_payload": self._json_safe(quote),
            }
        )
        snapshot["stale"] = False
        return self._quote_from_snapshot(snapshot)

    def get_metric(self, symbol: str, metric: str, *, normalized: bool = True) -> float | None:
        snapshot = self.get_metric_snapshot(symbol, metric)
        return self._metric_value_from_snapshot(snapshot, metric, normalized=normalized)

    def get_metric_snapshot(self, symbol: str, metric: str) -> dict[str, Any]:
        symbol = normalize_symbol(symbol)
        metric = metric.lower()
        if not is_supported_metric(metric):
            raise ValueError(f"Invalid metric: {metric}")

        now = self._now()
        fresh = self._get_fresh_snapshot(symbol, metric, now)
        if fresh:
            return fresh

        try:
            raw_value = self.provider.get_metric(symbol, metric)
            self._record_provider_ok(now)
        except Exception as error:
            self._record_provider_error(error, now, symbol=symbol, metric=metric)
            stale = self._get_latest_snapshot(symbol, metric)
            if stale:
                stale["stale"] = True
                return stale
            raise

        value = normalize_metric_value(metric, raw_value) if raw_value is not None else None
        definition = get_metric_definition(metric)
        snapshot = self._save_snapshot(
            {
                "symbol": symbol,
                "metric": metric,
                "value": value,
                "unit": definition.unit,
                "currency": None,
                "source": self._provider_source(),
                "as_of_date": None,
                "fetched_at": now,
                "expires_at": self._expires_at(now, self._metric_data_type(metric)),
                "confidence": DEFAULT_PROVIDER_CONFIDENCE,
                "raw_payload": self._json_safe({"raw_value": raw_value}),
            }
        )
        snapshot["stale"] = False
        return snapshot

    def get_price_history(self, symbol: str, period: str) -> list[dict[str, float | str]]:
        symbol = normalize_symbol(symbol)
        metric_key = f"price_history:{period.lower()}"
        now = self._now()
        fresh = self._get_fresh_snapshot(symbol, metric_key, now)
        if fresh:
            return self._history_from_snapshot(fresh)

        try:
            if hasattr(self.provider, "price_history_points"):
                points = self.provider.price_history_points(symbol, period)
            else:
                history = self.provider.get_price_history(symbol, period)
                from market_data.normalizers import price_history_points

                points = price_history_points(history)
            self._record_provider_ok(now)
        except Exception as error:
            self._record_provider_error(error, now, symbol=symbol, metric=metric_key)
            stale = self._get_latest_snapshot(symbol, metric_key)
            if stale:
                return self._history_from_snapshot(stale)
            raise

        self._save_snapshot(
            {
                "symbol": symbol,
                "metric": metric_key,
                "value": self._last_history_value(points),
                "unit": "currency",
                "currency": None,
                "source": self._provider_source(),
                "as_of_date": self._last_history_date(points),
                "fetched_at": now,
                "expires_at": self._expires_at(now, "price"),
                "confidence": DEFAULT_PROVIDER_CONFIDENCE,
                "raw_payload": self._json_safe(points),
            }
        )
        return points

    def get_metric_history(self, symbol: str, metric: str, period: str) -> list[dict[str, float | str]]:
        symbol = normalize_symbol(symbol)
        metric = metric.lower()
        if not is_supported_metric(metric):
            raise ValueError("Unsupported metric for history")

        metric_key = f"metric_history:{metric}:{period.lower()}"
        now = self._now()
        fresh = self._get_fresh_snapshot(symbol, metric_key, now)
        if fresh:
            return self._history_from_snapshot(fresh)

        try:
            points = self.provider.get_metric_history(symbol, metric, period)
            self._record_provider_ok(now)
        except Exception as error:
            self._record_provider_error(error, now, symbol=symbol, metric=metric_key)
            stale = self._get_latest_snapshot(symbol, metric_key)
            if stale:
                return self._history_from_snapshot(stale)
            raise

        definition = get_metric_definition(metric)
        self._save_snapshot(
            {
                "symbol": symbol,
                "metric": metric_key,
                "value": self._last_history_value(points),
                "unit": definition.unit,
                "currency": None,
                "source": self._provider_source(),
                "as_of_date": self._last_history_date(points),
                "fetched_at": now,
                "expires_at": self._expires_at(now, self._metric_history_data_type(metric)),
                "confidence": DEFAULT_PROVIDER_CONFIDENCE,
                "raw_payload": self._json_safe(points),
            }
        )
        return points

    def search_symbols(self, query: str) -> list[dict[str, str | None]]:
        if not query.strip():
            return []
        return self.provider.search_symbols(query.strip())

    def get_provider_health(self) -> list[dict[str, Any]]:
        return self.snapshot_repository.get_provider_health()

    def _now(self) -> datetime:
        now = self.clock()
        if now.tzinfo is None:
            return now.replace(tzinfo=timezone.utc)
        return now

    def _provider_source(self) -> str:
        return getattr(self.provider, "source", self.provider.__class__.__name__)

    def _ttl(self, data_type: str) -> int:
        return self.ttl_seconds.get(data_type, self.ttl_seconds["fundamentals"])

    def _expires_at(self, fetched_at: datetime, data_type: str) -> datetime:
        return fetched_at + timedelta(seconds=self._ttl(data_type))

    @staticmethod
    def _metric_data_type(metric: str) -> str:
        return "price" if metric == "price" else "fundamentals"

    @staticmethod
    def _metric_history_data_type(metric: str) -> str:
        return "price" if metric == "price" else "statements"

    def _get_fresh_snapshot(self, symbol: str, metric: str, now: datetime) -> dict[str, Any] | None:
        try:
            snapshot = self.snapshot_repository.get_fresh_metric_snapshot(symbol, metric, now)
        except Exception:
            logger.warning("Metric cache read failed for %s %s", symbol, metric, exc_info=True)
            return None
        if not snapshot:
            return None
        return self._snapshot_with_stale(snapshot, stale=False)

    def _get_latest_snapshot(self, symbol: str, metric: str) -> dict[str, Any] | None:
        try:
            snapshot = self.snapshot_repository.get_latest_metric_snapshot(symbol, metric)
        except Exception:
            logger.warning("Metric cache stale read failed for %s %s", symbol, metric, exc_info=True)
            return None
        if not snapshot:
            return None
        return self._snapshot_with_stale(snapshot, stale=True)

    @staticmethod
    def _snapshot_with_stale(snapshot: dict[str, Any], *, stale: bool) -> dict[str, Any]:
        payload = dict(snapshot)
        payload["stale"] = stale
        return payload

    def _save_snapshot(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        try:
            saved = self.snapshot_repository.save_metric_snapshot(snapshot)
        except Exception:
            logger.warning(
                "Metric cache write failed for %s %s",
                snapshot.get("symbol"),
                snapshot.get("metric"),
                exc_info=True,
            )
            return dict(snapshot)

        return dict(saved or snapshot)

    def _record_provider_ok(self, checked_at: datetime) -> None:
        try:
            self.snapshot_repository.upsert_provider_health(
                self._provider_source(),
                "ok",
                last_ok_at=checked_at,
            )
        except Exception:
            logger.warning("Provider health update failed for %s", self._provider_source(), exc_info=True)

    def _record_provider_error(
        self,
        error: Exception,
        checked_at: datetime,
        *,
        symbol: str,
        metric: str,
    ) -> None:
        logger.exception(
            "Provider %s failed while fetching %s for %s",
            self._provider_source(),
            metric,
            symbol,
        )
        try:
            self.snapshot_repository.upsert_provider_health(
                self._provider_source(),
                "error",
                last_error_at=checked_at,
                last_error=str(error),
            )
        except Exception:
            logger.warning("Provider health update failed for %s", self._provider_source(), exc_info=True)

    def _metric_value_from_snapshot(
        self,
        snapshot: dict[str, Any],
        metric: str,
        *,
        normalized: bool,
    ) -> float | None:
        if normalized:
            return to_float(snapshot.get("value"))

        raw_payload = snapshot.get("raw_payload")
        if isinstance(raw_payload, dict):
            raw_value = to_float(raw_payload.get("raw_value"))
            if raw_value is not None:
                return raw_value

        value = to_float(snapshot.get("value"))
        if value is None:
            return None

        multiplier = get_metric_definition(metric).multiplier
        return value / multiplier if multiplier else value

    @staticmethod
    def _quote_from_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
        raw_payload = snapshot.get("raw_payload")
        quote = dict(raw_payload) if isinstance(raw_payload, dict) else {}
        quote.setdefault("symbol", snapshot.get("symbol"))
        quote.setdefault("source", snapshot.get("source"))
        if quote.get("price") is None and snapshot.get("value") is not None:
            quote["price"] = snapshot.get("value")
        quote["stale"] = bool(snapshot.get("stale"))
        quote["fetched_at"] = snapshot.get("fetched_at")
        quote["expires_at"] = snapshot.get("expires_at")
        if snapshot.get("as_of_date") is not None:
            quote["as_of_date"] = snapshot.get("as_of_date")
        return quote

    @staticmethod
    def _history_from_snapshot(snapshot: dict[str, Any]) -> list[dict[str, float | str]]:
        raw_payload = snapshot.get("raw_payload")
        if isinstance(raw_payload, list):
            return raw_payload
        if isinstance(raw_payload, dict) and isinstance(raw_payload.get("points"), list):
            return raw_payload["points"]
        return []

    @staticmethod
    def _last_history_value(points: list[dict[str, float | str]]) -> float | None:
        for point in reversed(points):
            value = to_float(point.get("value"))
            if value is not None:
                return value
        return None

    @staticmethod
    def _last_history_date(points: list[dict[str, float | str]]) -> date | None:
        for point in reversed(points):
            raw_date = point.get("date")
            if raw_date is None:
                continue
            try:
                return datetime.fromisoformat(str(raw_date)).date()
            except ValueError:
                continue
        return None

    @staticmethod
    def _quote_as_of_date(quote: dict[str, Any]) -> date | None:
        for key in ("regularMarketTime", "postMarketTime", "preMarketTime"):
            timestamp = to_float(quote.get(key))
            if timestamp is None:
                continue
            try:
                return datetime.fromtimestamp(timestamp, tz=timezone.utc).date()
            except (OverflowError, OSError, ValueError):
                continue
        return None

    @classmethod
    def _json_safe(cls, value: Any) -> Any:
        if isinstance(value, dict):
            return {str(key): cls._json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [cls._json_safe(item) for item in value]
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, float):
            return value if math.isfinite(value) else None
        if value is None or isinstance(value, (str, int, bool)):
            return value
        if hasattr(value, "item"):
            try:
                return cls._json_safe(value.item())
            except (TypeError, ValueError):
                pass
        return str(value)


_market_data_service: MarketDataService | None = None


def get_market_data_service() -> MarketDataService:
    global _market_data_service
    if _market_data_service is None:
        _market_data_service = MarketDataService()
    return _market_data_service
