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


def test_deprecated_ticker_metric_alert_routes_return_409_for_duplicate_metric(
    monkeypatch,
    duplicate_pe_watchlist,
):
    monkeypatch.setenv("API_AUTH_TOKEN", "test-token")
    monkeypatch.delenv("READONLY_PUBLIC", raising=False)

    def fail_update_alert_target(alert_id, new_target):
        raise AssertionError("deprecated update must not mutate ambiguous ticker+metric alerts")

    def fail_delete_alert_db(alert_id=None, symbol=None, metric=None):
        raise AssertionError("deprecated delete must not mutate ambiguous ticker+metric alerts")

    monkeypatch.setattr(api_module.db, "get_watchlist", lambda: deepcopy(duplicate_pe_watchlist))
    monkeypatch.setattr(api_module.db, "update_alert_target", fail_update_alert_target)
    monkeypatch.setattr(api_module.db, "delete_alert_db", fail_delete_alert_db)

    client = TestClient(app)

    update_response = client.put(
        "/update",
        headers=AUTH_HEADER,
        json={"ticker": "AAPL", "metric": "pe", "value": 18},
    )
    delete_response = client.delete("/remove/AAPL/pe", headers=AUTH_HEADER)

    assert update_response.status_code == 409
    assert "Multiple alerts match" in update_response.json()["detail"]
    assert delete_response.status_code == 409
    assert "Multiple alerts match" in delete_response.json()["detail"]


def test_deprecated_ticker_metric_alert_routes_update_and_delete_single_match(monkeypatch):
    monkeypatch.setenv("API_AUTH_TOKEN", "test-token")
    monkeypatch.delenv("READONLY_PUBLIC", raising=False)

    state = {
        "AAPL": {
            "name": "Apple Inc.",
            "alerts": [
                {
                    "id": "alert-pe",
                    "metric": "pe",
                    "operator": "<",
                    "target": 20,
                    "is_active": True,
                    "is_triggered": False,
                    "reference_value": None,
                    "alert_type": "absolute",
                    "current_value": 25,
                }
            ],
        }
    }
    deleted_tickers = []

    def fake_get_watchlist():
        return deepcopy(state)

    def fake_update_alert_target(alert_id, new_target):
        assert alert_id == "alert-pe"
        state["AAPL"]["alerts"][0]["target"] = float(new_target)
        return [deepcopy(state["AAPL"]["alerts"][0])]

    def fake_delete_alert_db(alert_id=None, symbol=None, metric=None):
        assert alert_id == "alert-pe"
        assert symbol is None
        assert metric is None
        state["AAPL"]["alerts"] = []
        return True

    def fake_delete_ticker_db(symbol):
        deleted_tickers.append(symbol)
        state.pop(symbol, None)
        return True

    monkeypatch.setattr(api_module.db, "get_watchlist", fake_get_watchlist)
    monkeypatch.setattr(api_module.db, "update_alert_target", fake_update_alert_target)
    monkeypatch.setattr(api_module.db, "delete_alert_db", fake_delete_alert_db)
    monkeypatch.setattr(api_module.db, "delete_ticker_db", fake_delete_ticker_db)

    client = TestClient(app)

    update_response = client.put(
        "/update",
        headers=AUTH_HEADER,
        json={"ticker": "aapl", "metric": "PE", "value": 18},
    )
    delete_response = client.delete("/remove/aapl/PE", headers=AUTH_HEADER)

    assert update_response.status_code == 200
    assert update_response.json() == {"message": "Alert updated"}
    assert delete_response.status_code == 200
    assert delete_response.json() == {"message": "Alert removed"}
    assert state == {"AAPL": {"name": "Apple Inc.", "alerts": []}}
    assert deleted_tickers == []


def test_alert_delete_restore_and_history_durability(monkeypatch):
    monkeypatch.setenv("API_AUTH_TOKEN", "test-token")
    monkeypatch.delenv("READONLY_PUBLIC", raising=False)

    alerts = [
        {
            "id": "relative-1",
            "metric": "price",
            "operator": ">=",
            "target": 10.0,
            "is_active": True,
            "is_triggered": False,
            "reference_value": 100.0,
            "alert_type": "relative",
            "current_value": 105.0,
            "deleted_at": None,
            "restored_at": None,
        }
    ]
    history = [
        {
            "id": "history-1",
            "alert_id": "relative-1",
            "ticker_symbol": "AAPL",
            "company_name": "Apple Inc.",
            "metric": "price",
            "operator": ">=",
            "alert_type": "relative",
            "reference_value": 100.0,
            "trigger_value": 115.0,
            "target_value": 10.0,
        }
    ]

    def fake_get_watchlist():
        active_alerts = [
            {key: value for key, value in alert.items() if key not in {"deleted_at", "restored_at"}}
            for alert in alerts
            if alert["deleted_at"] is None
        ]
        return {"AAPL": {"name": "Apple Inc.", "alerts": deepcopy(active_alerts)}}

    def fake_delete_alert_db(alert_id=None, symbol=None, metric=None):
        assert alert_id == "relative-1"
        for alert in alerts:
            if alert["id"] == alert_id:
                alert["deleted_at"] = "2026-05-08T12:00:00+00:00"
                return [deepcopy(alert)]
        return []

    def fake_restore_alert_db(alert_id):
        assert alert_id == "relative-1"
        for alert in alerts:
            if alert["id"] == alert_id:
                alert["deleted_at"] = None
                alert["restored_at"] = "2026-05-08T12:01:00+00:00"
                return [deepcopy(alert)]
        return []

    monkeypatch.setattr(api_module.db, "get_watchlist", fake_get_watchlist)
    monkeypatch.setattr(api_module.db, "delete_alert_db", fake_delete_alert_db)
    monkeypatch.setattr(api_module.db, "restore_alert_db", fake_restore_alert_db)
    monkeypatch.setattr(api_module.db, "get_alert_history_db", lambda limit=50: deepcopy(history))

    client = TestClient(app)

    delete_response = client.delete("/alerts/relative-1", headers=AUTH_HEADER)
    watchlist_after_delete = client.get("/watchlist", headers=AUTH_HEADER).json()
    history_after_delete = client.get("/alert-history", headers=AUTH_HEADER).json()

    assert delete_response.status_code == 200
    assert watchlist_after_delete["AAPL"]["alerts"] == []
    assert history_after_delete == history

    restore_response = client.post("/alerts/relative-1/restore", headers=AUTH_HEADER)
    restored_alert = client.get("/watchlist", headers=AUTH_HEADER).json()["AAPL"]["alerts"][0]

    assert restore_response.status_code == 200
    assert restored_alert["id"] == "relative-1"
    assert restored_alert["target"] == 10.0
    assert restored_alert["operator"] == ">="
    assert restored_alert["alert_type"] == "relative"
    assert restored_alert["reference_value"] == 100.0
