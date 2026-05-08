from __future__ import annotations

from pydantic import BaseModel


class ScanSettingsRequest(BaseModel):
    interval_seconds: int
