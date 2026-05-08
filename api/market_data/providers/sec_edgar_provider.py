from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from market_data.normalizers import normalize_symbol, to_float
from market_data.providers.base import MarketDataProvider


SEC_TICKER_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_COMPANY_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts"
DEFAULT_SEC_USER_AGENT = "FundamenTracker contact@example.com"


SEC_METRIC_CONCEPTS: dict[str, tuple[str, ...]] = {
    "revenue": (
        "Revenues",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "SalesRevenueNet",
    ),
    "net_income": ("NetIncomeLoss",),
    "total_assets": ("Assets",),
    "total_liabilities": ("Liabilities",),
    "stockholders_equity": ("StockholdersEquity",),
    "operating_cash_flow": ("NetCashProvidedByUsedInOperatingActivities",),
    "capex": ("PaymentsToAcquirePropertyPlantAndEquipment",),
}


class SecEdgarError(Exception):
    """Base class for controlled SEC EDGAR provider errors."""


class SecEdgarRequestError(SecEdgarError):
    """Raised when an SEC EDGAR HTTP request fails."""


class SecTickerNotFoundError(SecEdgarError):
    def __init__(self, symbol: str):
        super().__init__(f"No SEC CIK mapping found for ticker '{symbol}'.")
        self.symbol = symbol


class SecConceptNotFoundError(SecEdgarError):
    def __init__(self, symbol: str, concept: str):
        super().__init__(f"No SEC us-gaap concept '{concept}' found for ticker '{symbol}'.")
        self.symbol = symbol
        self.concept = concept


class SecUnitNotFoundError(SecEdgarError):
    def __init__(self, symbol: str, concept: str, unit: str):
        super().__init__(
            f"No SEC unit '{unit}' found for us-gaap concept '{concept}' and ticker '{symbol}'."
        )
        self.symbol = symbol
        self.concept = concept
        self.unit = unit


class SecUnsupportedMetricError(SecEdgarError):
    def __init__(self, metric: str):
        supported = ", ".join(sorted(SEC_METRIC_CONCEPTS))
        super().__init__(f"Unsupported SEC metric '{metric}'. Supported metrics: {supported}.")
        self.metric = metric


class SecEdgarProvider(MarketDataProvider):
    source = "sec"

    def __init__(
        self,
        *,
        user_agent: str | None = None,
        requests_client=requests,
        request_timeout_seconds: int = 10,
        min_request_interval_seconds: float | None = None,
        ticker_cache_ttl_seconds: int = 24 * 60 * 60,
        ticker_cache_path: str | Path | None = None,
        clock=time.monotonic,
        sleeper=time.sleep,
    ):
        self.user_agent = (
            user_agent
            or os.getenv("SEC_USER_AGENT")
            or DEFAULT_SEC_USER_AGENT
        ).strip() or DEFAULT_SEC_USER_AGENT
        self.requests_client = requests_client
        self.request_timeout_seconds = request_timeout_seconds
        self.min_request_interval_seconds = (
            _env_float("SEC_RATE_LIMIT_SECONDS", 0.2)
            if min_request_interval_seconds is None
            else min_request_interval_seconds
        )
        cache_path = (
            ticker_cache_path
            if ticker_cache_path is not None
            else os.getenv("SEC_TICKER_CACHE_PATH")
        )
        self.ticker_cache_path = Path(cache_path).expanduser() if cache_path else None
        self.ticker_cache_ttl_seconds = ticker_cache_ttl_seconds
        self.clock = clock
        self.sleeper = sleeper
        self._last_request_at: float | None = None
        self._ticker_map_cache: tuple[float, dict[str, dict[str, str | None]]] | None = None
        self._company_facts_cache: dict[str, dict[str, Any]] = {}

    def ticker_to_cik(self, symbol: str) -> str:
        symbol = normalize_symbol(symbol)
        mapping = self._get_ticker_map()
        record = mapping.get(symbol)
        if record is None:
            raise SecTickerNotFoundError(symbol)
        cik = record.get("cik")
        if not cik:
            raise SecTickerNotFoundError(symbol)
        return format_cik(cik)

    def get_company_facts(self, cik: str | int) -> dict[str, Any]:
        formatted_cik = format_cik(cik)
        if formatted_cik in self._company_facts_cache:
            return self._company_facts_cache[formatted_cik]

        data = self._request_json(f"{SEC_COMPANY_FACTS_URL}/CIK{formatted_cik}.json")
        self._company_facts_cache[formatted_cik] = data
        return data

    def extract_us_gaap_metric(self, symbol: str, concept: str, unit: str = "USD") -> dict[str, Any]:
        symbol = normalize_symbol(symbol)
        concept = _normalize_concept(concept)
        cik = self.ticker_to_cik(symbol)
        company_facts = self.get_company_facts(cik)
        concept_block = company_facts.get("facts", {}).get("us-gaap", {}).get(concept)
        if not concept_block:
            raise SecConceptNotFoundError(symbol, concept)

        facts_for_unit = concept_block.get("units", {}).get(unit)
        if not facts_for_unit:
            raise SecUnitNotFoundError(symbol, concept, unit)

        selected_fact = _select_latest_fact(facts_for_unit)
        if selected_fact is None:
            raise SecConceptNotFoundError(symbol, concept)

        value = to_float(selected_fact.get("val"))
        if value is None:
            raise SecConceptNotFoundError(symbol, concept)

        return {
            "symbol": symbol,
            "cik": cik,
            "company_name": company_facts.get("entityName") or self._company_name(symbol),
            "source": self.source,
            "taxonomy": "us-gaap",
            "concept": concept,
            "label": concept_block.get("label"),
            "description": concept_block.get("description"),
            "unit": unit,
            "value": value,
            "start_date": selected_fact.get("start"),
            "as_of_date": selected_fact.get("end"),
            "filed_at": selected_fact.get("filed"),
            "form": selected_fact.get("form"),
            "fiscal_year": selected_fact.get("fy"),
            "fiscal_period": selected_fact.get("fp"),
            "frame": selected_fact.get("frame"),
            "accession": selected_fact.get("accn"),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

    def get_metric_snapshot(self, symbol: str, metric: str, unit: str = "USD") -> dict[str, Any]:
        metric = metric.strip().lower()
        concepts = SEC_METRIC_CONCEPTS.get(metric)
        if concepts is None:
            raise SecUnsupportedMetricError(metric)

        last_error: SecEdgarError | None = None
        for concept in concepts:
            try:
                snapshot = self.extract_us_gaap_metric(symbol, concept, unit)
                snapshot["metric"] = metric
                return snapshot
            except (SecConceptNotFoundError, SecUnitNotFoundError) as exc:
                last_error = exc

        raise SecConceptNotFoundError(normalize_symbol(symbol), " or ".join(concepts)) from last_error

    def get_basic_metrics(self, symbol: str, unit: str = "USD") -> dict[str, dict[str, Any]]:
        metrics: dict[str, dict[str, Any]] = {}
        for metric in SEC_METRIC_CONCEPTS:
            try:
                metrics[metric] = self.get_metric_snapshot(symbol, metric, unit)
            except (SecConceptNotFoundError, SecUnitNotFoundError):
                continue
        return metrics

    def get_quote(self, symbol: str) -> dict[str, Any]:
        symbol = normalize_symbol(symbol)
        cik = self.ticker_to_cik(symbol)
        return {
            "symbol": symbol,
            "cik": cik,
            "name": self._company_name(symbol) or symbol,
            "source": self.source,
        }

    def get_metric(self, symbol: str, metric: str) -> float | None:
        return to_float(self.get_metric_snapshot(symbol, metric).get("value"))

    def get_price_history(self, symbol: str, period: str) -> pd.DataFrame:
        return pd.DataFrame()

    def get_metric_history(self, symbol: str, metric: str, period: str) -> list[dict[str, float | str]]:
        snapshot = self.get_metric_snapshot(symbol, metric)
        date = snapshot.get("as_of_date")
        value = to_float(snapshot.get("value"))
        if date is None or value is None:
            return []
        return [{"date": str(date), "value": value}]

    def search_symbols(self, query: str) -> list[dict[str, str | None]]:
        query = query.strip().upper()
        if not query:
            return []
        results: list[dict[str, str | None]] = []
        for symbol, record in self._get_ticker_map().items():
            title = record.get("title")
            if query in symbol or (title and query in title.upper()):
                results.append({"symbol": symbol, "name": title})
            if len(results) >= 5:
                break
        return results

    def _request_json(self, url: str) -> dict[str, Any]:
        self._rate_limit()
        response = self.requests_client.get(
            url,
            headers=self._headers(),
            timeout=self.request_timeout_seconds,
        )
        if not getattr(response, "ok", False):
            status_code = getattr(response, "status_code", "unknown")
            raise SecEdgarRequestError(f"SEC EDGAR request failed with status {status_code}: {url}")
        try:
            return response.json()
        except ValueError as exc:
            raise SecEdgarRequestError(f"SEC EDGAR returned invalid JSON: {url}") from exc

    def _rate_limit(self) -> None:
        if self.min_request_interval_seconds <= 0:
            self._last_request_at = self.clock()
            return

        now = self.clock()
        if self._last_request_at is not None:
            elapsed = now - self._last_request_at
            wait_seconds = self.min_request_interval_seconds - elapsed
            if wait_seconds > 0:
                self.sleeper(wait_seconds)
                now = self.clock()
        self._last_request_at = now

    def _headers(self) -> dict[str, str]:
        return {
            "User-Agent": self.user_agent,
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate",
        }

    def _get_ticker_map(self) -> dict[str, dict[str, str | None]]:
        now = time.time()
        if self._ticker_map_cache is not None:
            cached_at, mapping = self._ticker_map_cache
            if now - cached_at < self.ticker_cache_ttl_seconds:
                return mapping

        cached_payload = self._read_ticker_cache()
        if cached_payload is not None:
            mapping = _normalize_ticker_payload(cached_payload)
            self._ticker_map_cache = (now, mapping)
            return mapping

        payload = self._request_json(SEC_TICKER_URL)
        self._write_ticker_cache(payload)
        mapping = _normalize_ticker_payload(payload)
        self._ticker_map_cache = (now, mapping)
        return mapping

    def _read_ticker_cache(self) -> dict[str, Any] | None:
        if self.ticker_cache_path is None or not self.ticker_cache_path.exists():
            return None
        cache_age_seconds = time.time() - self.ticker_cache_path.stat().st_mtime
        if cache_age_seconds >= self.ticker_cache_ttl_seconds:
            return None
        try:
            return json.loads(self.ticker_cache_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def _write_ticker_cache(self, payload: dict[str, Any]) -> None:
        if self.ticker_cache_path is None:
            return
        try:
            self.ticker_cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.ticker_cache_path.write_text(json.dumps(payload), encoding="utf-8")
        except OSError:
            return

    def _company_name(self, symbol: str) -> str | None:
        record = self._get_ticker_map().get(normalize_symbol(symbol))
        return record.get("title") if record else None


def format_cik(cik: str | int) -> str:
    digits = "".join(character for character in str(cik).strip() if character.isdigit())
    if not digits:
        raise SecEdgarError(f"Invalid SEC CIK value: {cik!r}")
    return digits.zfill(10)


def _normalize_concept(concept: str) -> str:
    normalized = concept.strip()
    if normalized.lower().startswith("us-gaap:"):
        return normalized.split(":", 1)[1]
    return normalized


def _normalize_ticker_payload(payload: dict[str, Any]) -> dict[str, dict[str, str | None]]:
    if isinstance(payload.get("tickers"), dict):
        records = payload["tickers"].values()
    else:
        records = payload.values()

    mapping: dict[str, dict[str, str | None]] = {}
    for record in records:
        if not isinstance(record, dict):
            continue
        symbol = record.get("ticker") or record.get("symbol")
        cik = record.get("cik_str") or record.get("cik")
        if not symbol or not cik:
            continue
        mapping[normalize_symbol(str(symbol))] = {
            "cik": format_cik(cik),
            "title": record.get("title") or record.get("name"),
        }
    return mapping


def _select_latest_fact(facts: list[dict[str, Any]]) -> dict[str, Any] | None:
    valid_facts = [
        fact
        for fact in facts
        if isinstance(fact, dict) and fact.get("end") and to_float(fact.get("val")) is not None
    ]
    if not valid_facts:
        return None

    return max(
        valid_facts,
        key=lambda fact: (
            str(fact.get("end") or ""),
            str(fact.get("filed") or ""),
            _form_priority(fact.get("form")),
            str(fact.get("accn") or ""),
        ),
    )


def _form_priority(form: Any) -> int:
    normalized = str(form or "").upper()
    if normalized.startswith("10-K"):
        return 3
    if normalized.startswith("10-Q"):
        return 2
    return 1


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return max(float(value), 0.0)
    except ValueError:
        return default
