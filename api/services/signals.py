from __future__ import annotations

from typing import Any


VALID_SIGNAL_STATUSES = {"open", "all"}


def normalize_limit(limit: int) -> int:
    return max(1, min(limit, 100))


def get_signals(db: Any, status: str = "open", limit: int = 50) -> list[dict[str, Any]]:
    if status not in VALID_SIGNAL_STATUSES:
        raise ValueError("Invalid signal status")
    return db.get_signals(status=status, limit=normalize_limit(limit))


def acknowledge_signal(db: Any, signal_id: str) -> dict[str, Any] | None:
    return db.acknowledge_signal(signal_id)


def dismiss_signal(db: Any, signal_id: str) -> dict[str, Any] | None:
    return db.dismiss_signal(signal_id)
