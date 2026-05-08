from __future__ import annotations

from pydantic import BaseModel


class ValuationRequest(BaseModel):
    ticker: str
