from __future__ import annotations

from copy import deepcopy

from db import client as db


class FakeAlertRepository:
    def __init__(self, tickers, alerts):
        self.tickers = deepcopy(tickers)
        self.alerts = deepcopy(alerts)

    def get_watchlist(self):
        alerts = [alert for alert in self.alerts if alert.get("deleted_at") is None]
        return db._build_watchlist(deepcopy(self.tickers), deepcopy(alerts))

    def update_alert_target(self, alert_id, new_target):
        for alert in self.alerts:
            if str(alert["id"]) == str(alert_id):
                alert["target_value"] = float(new_target)
                return [deepcopy(alert)]
        return []

    def delete_alert_db(self, alert_id=None, symbol=None, metric=None):
        changed = False
        if alert_id is not None:
            for alert in self.alerts:
                if str(alert["id"]) == str(alert_id):
                    alert["deleted_at"] = "2026-05-08T12:00:00+00:00"
                    changed = True
        elif symbol is not None and metric is not None:
            for alert in self.alerts:
                if alert["ticker_symbol"] == symbol and alert["metric"] == metric:
                    alert["deleted_at"] = "2026-05-08T12:00:00+00:00"
                    changed = True
        else:
            return False
        return changed

    def restore_alert_db(self, alert_id):
        for alert in self.alerts:
            if str(alert["id"]) == str(alert_id):
                alert["deleted_at"] = None
                alert["restored_at"] = "2026-05-08T12:01:00+00:00"
                return [deepcopy(alert)]
        return []


def alert_rows_from_watchlist(watchlist):
    return [
        {
            "id": alert["id"],
            "ticker_symbol": "AAPL",
            "metric": alert["metric"],
            "operator": alert["operator"],
            "target_value": alert["target"],
            "is_active": alert["is_active"],
            "is_triggered": alert["is_triggered"],
            "reference_value": alert["reference_value"],
            "alert_type": alert["alert_type"],
            "current_value": alert["current_value"],
            "current_source": alert.get("current_source"),
            "current_as_of_date": alert.get("current_as_of_date"),
            "current_fetched_at": alert.get("current_fetched_at"),
            "current_expires_at": alert.get("current_expires_at"),
            "current_stale": alert.get("current_stale"),
            "current_confidence": alert.get("current_confidence"),
            "deleted_at": alert.get("deleted_at"),
            "restored_at": alert.get("restored_at"),
        }
        for alert in watchlist["AAPL"]["alerts"]
    ]


def test_build_watchlist_preserves_duplicate_metric_alerts(duplicate_pe_watchlist):
    rows = alert_rows_from_watchlist(duplicate_pe_watchlist)

    watchlist = db._build_watchlist([{"symbol": "AAPL", "name": "Apple Inc."}], rows)

    assert watchlist == duplicate_pe_watchlist
    assert [alert["id"] for alert in watchlist["AAPL"]["alerts"]] == ["alert-low", "alert-high"]


def test_fake_repository_updates_one_duplicate_alert_by_id(duplicate_pe_watchlist):
    rows = alert_rows_from_watchlist(duplicate_pe_watchlist)
    repository = FakeAlertRepository([{"symbol": "AAPL", "name": "Apple Inc."}], rows)

    result = repository.update_alert_target("alert-high", 45.0)

    assert result[0]["id"] == "alert-high"
    assert repository.get_watchlist()["AAPL"]["alerts"] == [
        {
            **duplicate_pe_watchlist["AAPL"]["alerts"][0],
            "target": 20.0,
        },
        {
            **duplicate_pe_watchlist["AAPL"]["alerts"][1],
            "target": 45.0,
        },
    ]


def test_fake_repository_deletes_one_duplicate_alert_by_id(duplicate_pe_watchlist):
    rows = alert_rows_from_watchlist(duplicate_pe_watchlist)
    repository = FakeAlertRepository([{"symbol": "AAPL", "name": "Apple Inc."}], rows)

    assert repository.delete_alert_db(alert_id="alert-low") is True

    assert repository.get_watchlist()["AAPL"]["alerts"] == [
        duplicate_pe_watchlist["AAPL"]["alerts"][1]
    ]
    assert len(repository.alerts) == 2


def test_fake_repository_restores_deleted_alert_with_same_identity(duplicate_pe_watchlist):
    rows = alert_rows_from_watchlist(duplicate_pe_watchlist)
    repository = FakeAlertRepository([{"symbol": "AAPL", "name": "Apple Inc."}], rows)

    repository.delete_alert_db(alert_id="alert-low")
    restored = repository.restore_alert_db("alert-low")

    assert restored[0]["id"] == "alert-low"
    assert repository.get_watchlist()["AAPL"]["alerts"] == duplicate_pe_watchlist["AAPL"]["alerts"]
