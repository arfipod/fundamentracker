from __future__ import annotations

import pytest


@pytest.fixture
def duplicate_pe_watchlist():
    return {
        "AAPL": {
            "name": "Apple Inc.",
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
