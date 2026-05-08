from __future__ import annotations

import logging
import math
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from config import get_market_data_ttls
from market_data.metric_definitions import get_metric_catalog
from market_data.normalizers import normalize_symbol
from market_data.providers.sec_edgar_provider import (
    SEC_METRIC_CONCEPTS,
    SecConceptNotFoundError,
    SecEdgarError,
    SecEdgarProvider,
    SecTickerNotFoundError,
    SecUnitNotFoundError,
)
from repositories.factory import get_repository


DEFAULT_MARKET_OVERVIEW_TICKERS = ["SPY", "QQQ", "DIA"]
SEC_PROVIDER_SOURCE = "sec"
SEC_FACT_CONFIDENCE = 0.95
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


def get_sec_fundamentals(
    ticker: str,
    *,
    provider: Any | None = None,
    snapshot_repository: Any | None = None,
    clock: Any | None = None,
) -> dict[str, Any]:
    symbol = normalize_symbol(ticker)
    sec_provider = provider or SecEdgarProvider()
    repository = snapshot_repository or get_repository()
    now = _utc_now(clock)
    response: dict[str, Any] = {
        "ticker": symbol,
        "cik": None,
        "company_name": None,
        "facts": [],
        "errors": [],
    }

    try:
        cik = sec_provider.ticker_to_cik(symbol)
    except SecTickerNotFoundError as error:
        _record_sec_provider_ok(repository, now)
        response["errors"].append({"metric": None, "message": str(error)})
        return response
    except SecEdgarError as error:
        _record_sec_provider_error(repository, error, now)
        response["errors"].append({"metric": None, "message": str(error)})
        return response

    response["cik"] = cik
    provider_failed = False
    try:
        company_facts = sec_provider.get_company_facts(cik)
        response["company_name"] = company_facts.get("entityName")
    except SecEdgarError as error:
        _record_sec_provider_error(repository, error, now)
        response["errors"].append({"metric": None, "message": str(error)})
        return response

    for metric in SEC_METRIC_CONCEPTS:
        try:
            snapshot = sec_provider.get_metric_snapshot(symbol, metric)
        except (SecConceptNotFoundError, SecUnitNotFoundError) as error:
            response["errors"].append({"metric": metric, "message": str(error)})
            continue
        except SecEdgarError as error:
            provider_failed = True
            _record_sec_provider_error(repository, error, now)
            response["errors"].append({"metric": metric, "message": str(error)})
            continue

        if not response["company_name"]:
            response["company_name"] = snapshot.get("company_name")
        fact = _sec_fact_from_snapshot(snapshot)
        response["facts"].append(fact)
        _cache_sec_fact(repository, snapshot, now)

    if not provider_failed:
        _record_sec_provider_ok(repository, now)
    return response


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


def _utc_now(clock: Any | None) -> datetime:
    now = clock() if clock is not None else datetime.now(timezone.utc)
    if now.tzinfo is None:
        return now.replace(tzinfo=timezone.utc)
    return now


def _sec_fact_from_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        "metric": snapshot.get("metric"),
        "value": snapshot.get("value"),
        "unit": snapshot.get("unit"),
        "concept": snapshot.get("concept"),
        "label": snapshot.get("label"),
        "fiscal_year": snapshot.get("fiscal_year"),
        "fiscal_period": snapshot.get("fiscal_period"),
        "form": snapshot.get("form"),
        "as_of_date": snapshot.get("as_of_date"),
        "filed_at": snapshot.get("filed_at"),
        "accession": snapshot.get("accession"),
        "source": snapshot.get("source") or SEC_PROVIDER_SOURCE,
    }


def _cache_sec_fact(repository: Any, snapshot: dict[str, Any], fetched_at: datetime) -> None:
    ttl_seconds = get_market_data_ttls()["fundamentals"]
    cache_payload = {
        "symbol": snapshot.get("symbol"),
        "metric": snapshot.get("metric"),
        "value": snapshot.get("value"),
        "unit": snapshot.get("unit"),
        "currency": "USD" if snapshot.get("unit") == "USD" else None,
        "source": SEC_PROVIDER_SOURCE,
        "as_of_date": snapshot.get("as_of_date"),
        "fetched_at": fetched_at,
        "expires_at": fetched_at + timedelta(seconds=ttl_seconds),
        "confidence": SEC_FACT_CONFIDENCE,
        "raw_payload": _json_safe(snapshot),
    }
    try:
        repository.save_metric_snapshot(cache_payload)
    except Exception:
        logger.warning(
            "SEC metric cache write failed",
            extra={
                "ticker": snapshot.get("symbol"),
                "metric": snapshot.get("metric"),
                "provider": SEC_PROVIDER_SOURCE,
            },
            exc_info=True,
        )


def _record_sec_provider_ok(repository: Any, checked_at: datetime) -> None:
    try:
        repository.upsert_provider_health(SEC_PROVIDER_SOURCE, "ok", last_ok_at=checked_at)
    except Exception:
        logger.warning(
            "SEC provider health update failed",
            extra={"provider": SEC_PROVIDER_SOURCE},
            exc_info=True,
        )


def _record_sec_provider_error(repository: Any, error: Exception, checked_at: datetime) -> None:
    logger.warning(
        "SEC provider failed while fetching audited facts",
        extra={"provider": SEC_PROVIDER_SOURCE},
        exc_info=True,
    )
    try:
        repository.upsert_provider_health(
            SEC_PROVIDER_SOURCE,
            "error",
            last_error_at=checked_at,
            last_error=str(error),
        )
    except Exception:
        logger.warning(
            "SEC provider health update failed",
            extra={"provider": SEC_PROVIDER_SOURCE},
            exc_info=True,
        )


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if value is None or isinstance(value, (str, int, bool)):
        return value
    return str(value)
