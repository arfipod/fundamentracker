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
                },
            ],
        }
    }
