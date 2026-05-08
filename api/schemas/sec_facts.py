from __future__ import annotations

from pydantic import BaseModel, Field


class SecFact(BaseModel):
    metric: str
    value: float | None = None
    unit: str | None = None
    concept: str | None = None
    label: str | None = None
    fiscal_year: int | None = None
    fiscal_period: str | None = None
    form: str | None = None
    as_of_date: str | None = None
    filed_at: str | None = None
    accession: str | None = None
    source: str = "sec"


class SecFactError(BaseModel):
    metric: str | None = None
    message: str


class SecFundamentalsResponse(BaseModel):
    ticker: str
    cik: str | None = None
    company_name: str | None = None
    facts: list[SecFact] = Field(default_factory=list)
    errors: list[SecFactError] = Field(default_factory=list)
