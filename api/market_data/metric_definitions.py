from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MetricDefinition:
    key: str
    yf_key: str
    unit: str
    multiplier: float
    category: str
    label: str
    description: str
    higher_is_better: bool | None
    supported_for_alerts: bool
    supported_for_history: bool


METRIC_DEFINITIONS: dict[str, MetricDefinition] = {
    "pe": MetricDefinition(
        key="pe",
        yf_key="trailingPE",
        unit="ratio",
        multiplier=1.0,
        category="Valuation",
        label="Trailing P/E",
        description="Trailing price-to-earnings ratio.",
        higher_is_better=False,
        supported_for_alerts=True,
        supported_for_history=True,
    ),
    "fpe": MetricDefinition(
        key="fpe",
        yf_key="forwardPE",
        unit="ratio",
        multiplier=1.0,
        category="Valuation",
        label="Forward P/E",
        description="Forward price-to-earnings ratio based on analyst estimates.",
        higher_is_better=False,
        supported_for_alerts=True,
        supported_for_history=True,
    ),
    "pb": MetricDefinition(
        key="pb",
        yf_key="priceToBook",
        unit="ratio",
        multiplier=1.0,
        category="Valuation",
        label="Price to Book",
        description="Market price divided by book value per share.",
        higher_is_better=False,
        supported_for_alerts=True,
        supported_for_history=True,
    ),
    "evebitda": MetricDefinition(
        key="evebitda",
        yf_key="enterpriseToEbitda",
        unit="ratio",
        multiplier=1.0,
        category="Valuation",
        label="EV/EBITDA",
        description="Enterprise value divided by EBITDA.",
        higher_is_better=False,
        supported_for_alerts=True,
        supported_for_history=True,
    ),
    "roe": MetricDefinition(
        key="roe",
        yf_key="returnOnEquity",
        unit="percent",
        multiplier=100.0,
        category="Profitability",
        label="Return on Equity",
        description="Net income as a percentage of shareholder equity.",
        higher_is_better=True,
        supported_for_alerts=True,
        supported_for_history=True,
    ),
    "price": MetricDefinition(
        key="price",
        yf_key="currentPrice",
        unit="currency",
        multiplier=1.0,
        category="Price",
        label="Price",
        description="Current market price.",
        higher_is_better=None,
        supported_for_alerts=True,
        supported_for_history=True,
    ),
    "roic": MetricDefinition(
        key="roic",
        yf_key="roic",
        unit="percent",
        multiplier=100.0,
        category="Profitability",
        label="Return on Invested Capital",
        description="Return generated on invested capital when statement data is available.",
        higher_is_better=True,
        supported_for_alerts=True,
        supported_for_history=True,
    ),
    "dividendyield": MetricDefinition(
        key="dividendyield",
        yf_key="dividendYield",
        unit="percent",
        multiplier=100.0,
        category="Shareholder Return",
        label="Dividend Yield",
        description="Dividend yield as a percentage of price.",
        higher_is_better=True,
        supported_for_alerts=True,
        supported_for_history=True,
    ),
    "payoutratio": MetricDefinition(
        key="payoutratio",
        yf_key="payoutRatio",
        unit="percent",
        multiplier=100.0,
        category="Shareholder Return",
        label="Payout Ratio",
        description="Percentage of earnings paid as dividends.",
        higher_is_better=None,
        supported_for_alerts=True,
        supported_for_history=True,
    ),
    "debttoequity": MetricDefinition(
        key="debttoequity",
        yf_key="debtToEquity",
        unit="ratio",
        multiplier=1.0,
        category="Leverage",
        label="Debt to Equity",
        description="Total debt relative to shareholder equity.",
        higher_is_better=False,
        supported_for_alerts=True,
        supported_for_history=True,
    ),
    "profitmargins": MetricDefinition(
        key="profitmargins",
        yf_key="profitMargins",
        unit="percent",
        multiplier=100.0,
        category="Profitability",
        label="Profit Margins",
        description="Net profit margin as a percentage of revenue.",
        higher_is_better=True,
        supported_for_alerts=True,
        supported_for_history=True,
    ),
    "operatingmargins": MetricDefinition(
        key="operatingmargins",
        yf_key="operatingMargins",
        unit="percent",
        multiplier=100.0,
        category="Profitability",
        label="Operating Margins",
        description="Operating income as a percentage of revenue.",
        higher_is_better=True,
        supported_for_alerts=True,
        supported_for_history=True,
    ),
}

METRICS_MAP = {key: definition.yf_key for key, definition in METRIC_DEFINITIONS.items()}


def get_metric_catalog() -> list[dict[str, Any]]:
    catalog = [asdict(definition) for definition in METRIC_DEFINITIONS.values()]
    return sorted(catalog, key=lambda item: (item["category"], item["label"]))


def get_metric_definition(metric: str) -> MetricDefinition:
    return METRIC_DEFINITIONS[metric.lower()]


def is_supported_metric(metric: str) -> bool:
    return metric.lower() in METRIC_DEFINITIONS
