from __future__ import annotations

import json
import os
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from market_data.metric_definitions import get_metric_catalog
from market_data.normalizers import normalize_symbol, to_float
from schemas.valuation import (
    StructuredValuationFields,
    SuggestedAlert,
    ValuationResponse,
    ValuationSource,
)


class GenAILibraryNotInstalledError(Exception):
    pass


class GeminiApiKeyNotConfiguredError(Exception):
    pass


class InvalidAIValuationResponseError(Exception):
    pass


VALUATION_CATEGORIES = {"Valuation", "Profitability", "Leverage", "Shareholder Return"}
ALERT_OPERATORS = {"<", ">", "<=", ">=", "==", "=", "!="}
DISCLAIMER = (
    "This AI-generated analysis is for research and alert-triage only. It is based solely on "
    "the supplied data pack, may be incomplete or stale, and is not investment advice."
)


def generate_ai_valuation(market_data_service: Any, ticker: str) -> dict[str, Any]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise GeminiApiKeyNotConfiguredError(
            "GEMINI_API_KEY not configured. Please set it in your environment."
        )

    symbol = normalize_symbol(ticker)
    data_pack = build_valuation_data_pack(market_data_service, symbol)
    prompt = build_valuation_prompt(data_pack)
    raw_response = _generate_gemini_response(api_key, prompt)
    structured = _parse_structured_response(raw_response)
    response = _finalize_response(structured, data_pack)
    return response.model_dump()


def build_valuation_data_pack(market_data_service: Any, ticker: str) -> dict[str, Any]:
    symbol = normalize_symbol(ticker)
    quote = market_data_service.get_quote(symbol)
    quote_entry = _quote_entry(symbol, quote)
    metrics: list[dict[str, Any]] = []
    missing_data: list[str] = []

    for definition in _valuation_metric_definitions():
        metric = definition["key"]
        try:
            snapshot = market_data_service.get_metric_snapshot(symbol, metric)
        except Exception as error:
            missing_data.append(f"{definition['label']} unavailable: {error}")
            metrics.append(_missing_metric_entry(definition, str(error)))
            continue

        entry = _metric_entry(definition, snapshot)
        if entry["value"] is None:
            missing_data.append(f"{definition['label']} value is unavailable")
        metrics.append(entry)

    sources = [_source_from_quote(quote_entry)]
    sources.extend(_source_from_metric(metric) for metric in metrics)

    return {
        "ticker": symbol,
        "company_name": quote_entry["company_name"],
        "quote": quote_entry,
        "metrics": metrics,
        "sources": [source.model_dump() for source in sources],
        "backend_missing_data": missing_data,
        "limitations": [
            "No historical valuation norms are included unless present as explicit metrics.",
            "No peer or sector comparison data is included unless present as explicit metrics.",
            "Suggested alerts are read-only ideas and are not created automatically.",
        ],
    }


def build_valuation_prompt(data_pack: dict[str, Any]) -> str:
    schema = {
        "ticker": "string",
        "company_name": "string or null",
        "summary": "string",
        "valuation_label": "cheap | fair | expensive | inconclusive",
        "data_quality": "high | medium | low",
        "key_observations": ["string"],
        "risks": ["string"],
        "missing_data": ["string"],
        "suggested_alerts": [
            {
                "metric": "string",
                "operator": "string",
                "value": "number",
                "rationale": "string",
            }
        ],
        "sources": [
            {
                "metric": "string",
                "source": "string or null",
                "as_of_date": "string or null",
                "fetched_at": "string or null",
                "stale": "boolean or null",
            }
        ],
        "disclaimer": "string",
    }
    return (
        "You are analyzing a stock for a self-hosted fundamental alert tracker.\n"
        "Use only the JSON data pack below. Do not use outside knowledge, web knowledge, "
        "historical norms, sector averages, peer comparisons, or assumptions that are not "
        "explicitly present in the data pack.\n"
        "If the supplied data is insufficient for a valuation call, set valuation_label to "
        '"inconclusive" and explain the missing data instead of inventing it.\n'
        "Avoid investment advice, price targets, buy/sell/hold recommendations, and portfolio "
        "instructions. Suggested alerts must be read-only monitoring ideas based on available "
        "metrics, not recommendations to trade. Suggested alert metrics must be metric keys from "
        "data_pack.metrics, and operators must be one of <, >, <=, >=, ==, =, or !=.\n"
        "Return one JSON object only, with no markdown fences or commentary. The JSON object "
        "must match this shape exactly:\n"
        f"{json.dumps(schema, indent=2)}\n\n"
        "For sources, use only entries from data_pack.sources. Use this exact disclaimer:\n"
        f"{json.dumps(DISCLAIMER)}\n\n"
        "data_pack:\n"
        f"{json.dumps(_json_safe(data_pack), indent=2, sort_keys=True)}"
    )


def _valuation_metric_definitions() -> list[dict[str, Any]]:
    metrics = [
        metric
        for metric in get_metric_catalog()
        if metric["supported_for_alerts"] and metric["category"] in VALUATION_CATEGORIES
    ]
    return sorted(metrics, key=lambda item: (item["category"], item["label"]))


def _quote_entry(symbol: str, quote: dict[str, Any]) -> dict[str, Any]:
    price = to_float(quote.get("price") or quote.get("currentPrice") or quote.get("regularMarketPrice"))
    company_name = quote.get("longName") or quote.get("shortName") or quote.get("name")
    return {
        "metric": "quote",
        "symbol": quote.get("symbol") or symbol,
        "company_name": str(company_name) if company_name else None,
        "price": price,
        "currency": quote.get("currency"),
        "sector": quote.get("sector"),
        "industry": quote.get("industry"),
        "exchange": quote.get("exchange"),
        "market_cap": to_float(quote.get("marketCap")),
        "source": quote.get("source"),
        "as_of_date": _string_or_none(quote.get("as_of_date")),
        "fetched_at": _string_or_none(quote.get("fetched_at")),
        "stale": _bool_or_none(quote.get("stale")),
    }


def _metric_entry(definition: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        "metric": definition["key"],
        "label": definition["label"],
        "category": definition["category"],
        "description": definition["description"],
        "value": to_float(snapshot.get("value")),
        "unit": snapshot.get("unit") or definition["unit"],
        "higher_is_better": definition["higher_is_better"],
        "source": snapshot.get("source"),
        "as_of_date": _string_or_none(snapshot.get("as_of_date")),
        "fetched_at": _string_or_none(snapshot.get("fetched_at")),
        "stale": _bool_or_none(snapshot.get("stale")),
    }


def _missing_metric_entry(definition: dict[str, Any], error: str) -> dict[str, Any]:
    return {
        "metric": definition["key"],
        "label": definition["label"],
        "category": definition["category"],
        "description": definition["description"],
        "value": None,
        "unit": definition["unit"],
        "higher_is_better": definition["higher_is_better"],
        "source": None,
        "as_of_date": None,
        "fetched_at": None,
        "stale": None,
        "error": error,
    }


def _source_from_quote(quote: dict[str, Any]) -> ValuationSource:
    return ValuationSource(
        metric="quote",
        source=quote.get("source"),
        as_of_date=quote.get("as_of_date"),
        fetched_at=quote.get("fetched_at"),
        stale=quote.get("stale"),
    )


def _source_from_metric(metric: dict[str, Any]) -> ValuationSource:
    return ValuationSource(
        metric=metric["metric"],
        source=metric.get("source"),
        as_of_date=metric.get("as_of_date"),
        fetched_at=metric.get("fetched_at"),
        stale=metric.get("stale"),
    )


def _generate_gemini_response(api_key: str, prompt: str) -> str:
    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        raise GenAILibraryNotInstalledError("Google GenAI library not installed") from exc

    client = genai.Client(api_key=api_key)
    kwargs: dict[str, Any] = {"model": "gemini-2.5-flash", "contents": prompt}
    config = _gemini_json_config(types)
    if config is not None:
        kwargs["config"] = config

    response = client.models.generate_content(**kwargs)
    parsed = getattr(response, "parsed", None)
    if isinstance(parsed, StructuredValuationFields):
        return parsed.model_dump_json()
    if isinstance(parsed, dict):
        return json.dumps(parsed)

    text = getattr(response, "text", None)
    if not text:
        raise InvalidAIValuationResponseError("Gemini returned an empty valuation response")
    return str(text)


def _gemini_json_config(types: Any) -> Any | None:
    config_class = getattr(types, "GenerateContentConfig", None)
    if config_class is None:
        return None

    try:
        return config_class(
            temperature=0.2,
            response_mime_type="application/json",
            response_schema=StructuredValuationFields,
        )
    except Exception:
        try:
            return config_class(temperature=0.2, response_mime_type="application/json")
        except Exception:
            return None


def _parse_structured_response(raw_response: str) -> StructuredValuationFields:
    payload = _extract_json_object(raw_response)
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise InvalidAIValuationResponseError("Gemini returned invalid JSON") from exc

    try:
        return StructuredValuationFields.model_validate(data)
    except Exception as exc:
        raise InvalidAIValuationResponseError("Gemini returned JSON that did not match the valuation schema") from exc


def _extract_json_object(raw_response: str) -> str:
    text = raw_response.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)

    if text.startswith("{") and text.endswith("}"):
        return text

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise InvalidAIValuationResponseError("Gemini response did not contain a JSON object")
    return text[start : end + 1]


def _finalize_response(
    structured: StructuredValuationFields,
    data_pack: dict[str, Any],
) -> ValuationResponse:
    allowed_sources = {
        source["metric"]: ValuationSource.model_validate(source)
        for source in data_pack["sources"]
    }
    source_metrics = {source.metric for source in structured.sources}
    sources = [
        allowed_sources[source.metric]
        for source in structured.sources
        if source.metric in allowed_sources
    ]
    for metric, source in allowed_sources.items():
        if metric not in source_metrics:
            sources.append(source)

    missing_data = _dedupe_strings(
        [*data_pack.get("backend_missing_data", []), *structured.missing_data]
    )
    finalized = StructuredValuationFields(
        ticker=data_pack["ticker"],
        company_name=data_pack.get("company_name"),
        summary=structured.summary.strip(),
        valuation_label=structured.valuation_label,
        data_quality=structured.data_quality,
        key_observations=_dedupe_strings(structured.key_observations),
        risks=_dedupe_strings(structured.risks),
        missing_data=missing_data,
        suggested_alerts=_valid_suggested_alerts(structured, data_pack),
        sources=sources,
        disclaimer=DISCLAIMER,
    )
    return ValuationResponse(**finalized.model_dump(), analysis=_legacy_analysis(finalized))


def _valid_suggested_alerts(
    structured: StructuredValuationFields,
    data_pack: dict[str, Any],
) -> list[SuggestedAlert]:
    available_metrics = {
        metric["metric"]
        for metric in data_pack.get("metrics", [])
        if metric.get("value") is not None
    }
    return [
        alert
        for alert in structured.suggested_alerts
        if alert.metric in available_metrics and alert.operator in ALERT_OPERATORS
    ]


def _legacy_analysis(response: StructuredValuationFields) -> str:
    sections = [
        f"{response.valuation_label.title()} valuation signal. {response.summary}",
    ]
    if response.key_observations:
        sections.append("Key observations: " + "; ".join(response.key_observations))
    if response.risks:
        sections.append("Risks: " + "; ".join(response.risks))
    if response.missing_data:
        sections.append("Missing data: " + "; ".join(response.missing_data))
    sections.append(response.disclaimer)
    return "\n\n".join(sections)


def _dedupe_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        clean = value.strip()
        if not clean or clean in seen:
            continue
        seen.add(clean)
        output.append(clean)
    return output


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


def _bool_or_none(value: Any) -> bool | None:
    if value is None:
        return None
    return bool(value)


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value
