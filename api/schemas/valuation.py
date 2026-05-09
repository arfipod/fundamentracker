from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class ValuationRequest(BaseModel):
    ticker: str


class SuggestedAlert(BaseModel):
    metric: str
    operator: str
    value: float
    rationale: str


class ValuationSource(BaseModel):
    metric: str
    source: str | None
    as_of_date: str | None
    fetched_at: str | None
    stale: bool | None


class StructuredValuationFields(BaseModel):
    ticker: str
    company_name: str | None
    summary: str
    valuation_label: Literal["cheap", "fair", "expensive", "inconclusive"]
    data_quality: Literal["high", "medium", "low"]
    key_observations: list[str]
    risks: list[str]
    missing_data: list[str]
    suggested_alerts: list[SuggestedAlert]
    sources: list[ValuationSource]
    disclaimer: str


class ValuationResponse(StructuredValuationFields):
    analysis: str
