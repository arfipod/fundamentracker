from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MetricDefinition:
    key: str
    yf_key: str
    unit: str
    multiplier: float
    type: str


METRIC_DEFINITIONS: dict[str, MetricDefinition] = {
    "pe": MetricDefinition("pe", "trailingPE", "ratio", 1.0, "valuation"),
    "fpe": MetricDefinition("fpe", "forwardPE", "ratio", 1.0, "valuation"),
    "pb": MetricDefinition("pb", "priceToBook", "ratio", 1.0, "valuation"),
    "evebitda": MetricDefinition("evebitda", "enterpriseToEbitda", "ratio", 1.0, "valuation"),
    "roe": MetricDefinition("roe", "returnOnEquity", "percent", 100.0, "profitability"),
    "price": MetricDefinition("price", "currentPrice", "currency", 1.0, "price"),
    "roic": MetricDefinition("roic", "roic", "percent", 100.0, "profitability"),
    "dividendyield": MetricDefinition("dividendyield", "dividendYield", "percent", 100.0, "shareholder_return"),
    "payoutratio": MetricDefinition("payoutratio", "payoutRatio", "percent", 100.0, "shareholder_return"),
    "debttoequity": MetricDefinition("debttoequity", "debtToEquity", "ratio", 1.0, "leverage"),
    "profitmargins": MetricDefinition("profitmargins", "profitMargins", "percent", 100.0, "profitability"),
    "operatingmargins": MetricDefinition("operatingmargins", "operatingMargins", "percent", 100.0, "profitability"),
}

METRICS_MAP = {key: definition.yf_key for key, definition in METRIC_DEFINITIONS.items()}


def get_metric_definition(metric: str) -> MetricDefinition:
    return METRIC_DEFINITIONS[metric.lower()]


def is_supported_metric(metric: str) -> bool:
    return metric.lower() in METRIC_DEFINITIONS
