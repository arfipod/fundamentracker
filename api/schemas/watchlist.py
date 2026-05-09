from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class WatchlistMetadataRequest(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    notes: Optional[str] = None
    thesis: Optional[str] = None
    target_action: Optional[str] = None


class AddTickerTagRequest(BaseModel):
    name: str
    color: Optional[str] = None
