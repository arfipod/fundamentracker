from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class AddAlertRequest(BaseModel):
    ticker: str
    metric: str
    operator: str
    value: float
    alert_type: Optional[str] = "absolute"


class UpdateAlertRequest(BaseModel):
    ticker: str
    metric: str
    value: float


class UpdateAlertByIdRequest(BaseModel):
    value: float


class ToggleAlertRequest(BaseModel):
    is_active: bool
