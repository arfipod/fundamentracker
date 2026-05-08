from __future__ import annotations

import pytest


@pytest.fixture
def duplicate_pe_watchlist():
    return {
        "AAPL": {
            "name": "Apple Inc.",
            "status": "watching",
            "priority": "medium",
            "notes": None,
            "thesis": None,
            "target_action": None,
            "tags": [],
            "alerts": [
                {
                    "id": "alert-low",
                    "metric": "pe",
                    "operator": "<",
                    "target": 20.0,
                    "is_active": True,
                    "is_triggered": False,
                    "reference_value": None,
                    "alert_type": "absolute",
                    "current_value": None,
                    "current_source": None,
                    "current_as_of_date": None,
                    "current_fetched_at": None,
                    "current_expires_at": None,
                    "current_stale": None,
                    "current_confidence": None,
                },
                {
                    "id": "alert-high",
                    "metric": "pe",
                    "operator": ">",
                    "target": 40.0,
                    "is_active": True,
                    "is_triggered": False,
                    "reference_value": None,
                    "alert_type": "absolute",
                    "current_value": None,
                    "current_source": None,
                    "current_as_of_date": None,
                    "current_fetched_at": None,
                    "current_expires_at": None,
                    "current_stale": None,
                    "current_confidence": None,
                },
            ],
        }
    }
