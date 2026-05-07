from copy import deepcopy

from fastapi.testclient import TestClient

import api as api_module
from api import app


AUTH_HEADER = {"Authorization": "Bearer test-token"}


def test_alert_id_operations_affect_only_matching_duplicate_metric(monkeypatch):
    monkeypatch.setenv("API_AUTH_TOKEN", "test-token")
    monkeypatch.delenv("READONLY_PUBLIC", raising=False)

    state = {
        "AAPL": {
            "name": "Apple Inc.",
            "alerts": [
                {
                    "id": "alert-low",
                    "metric": "pe",
                    "operator": "<",
                    "target": 20,
                    "is_active": True,
                    "is_triggered": False,
                    "reference_value": None,
                    "alert_type": "absolute",
                    "current_value": 25,
                },
                {
                    "id": "alert-high",
                    "metric": "pe",
                    "operator": ">",
                    "target": 40,
                    "is_active": True,
                    "is_triggered": False,
                    "reference_value": None,
                    "alert_type": "absolute",
                    "current_value": 25,
                },
            ],
        }
    }
    deleted_tickers = []

    def fake_get_watchlist():
        return deepcopy(state)

    def fake_update_alert_target(alert_id, new_target):
        for details in state.values():
            for alert in details["alerts"]:
                if alert["id"] == alert_id:
                    alert["target"] = float(new_target)
                    return [deepcopy(alert)]
        return []

    def fake_delete_alert_db(alert_id=None, symbol=None, metric=None):
        if not alert_id:
            return False
        for details in state.values():
            before = len(details["alerts"])
            details["alerts"] = [alert for alert in details["alerts"] if alert["id"] != alert_id]
            if len(details["alerts"]) != before:
                return True
        return False

    def fake_delete_ticker_db(symbol):
        deleted_tickers.append(symbol)
        state.pop(symbol, None)
        return True

    monkeypatch.setattr(api_module.db, "get_watchlist", fake_get_watchlist)
    monkeypatch.setattr(api_module.db, "update_alert_target", fake_update_alert_target)
    monkeypatch.setattr(api_module.db, "delete_alert_db", fake_delete_alert_db)
    monkeypatch.setattr(api_module.db, "delete_ticker_db", fake_delete_ticker_db)

    client = TestClient(app)

    update_response = client.patch("/alerts/alert-high", headers=AUTH_HEADER, json={"value": 45})

    assert update_response.status_code == 200
    assert state["AAPL"]["alerts"][0]["target"] == 20
    assert state["AAPL"]["alerts"][1]["target"] == 45

    delete_response = client.delete("/alerts/alert-low", headers=AUTH_HEADER)

    assert delete_response.status_code == 200
    assert state["AAPL"]["alerts"] == [
        {
            "id": "alert-high",
            "metric": "pe",
            "operator": ">",
            "target": 45,
            "is_active": True,
            "is_triggered": False,
            "reference_value": None,
            "alert_type": "absolute",
            "current_value": 25,
        }
    ]
    assert deleted_tickers == []
