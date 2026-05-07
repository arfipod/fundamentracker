from __future__ import annotations

from copy import deepcopy
from unittest.mock import Mock

import scanner


class FakeMarketDataService:
    def __init__(self, values=None, errors=None):
        self.values = values or {}
        self.errors = errors or {}
        self.calls = []

    def get_metric(self, symbol, metric):
        self.calls.append((symbol, metric))
        key = (symbol, metric)
        if key in self.errors:
            raise self.errors[key]
        return self.values.get(key)


def install_fake_scanner_db(monkeypatch, watchlist):
    updates = []
    history = []

    monkeypatch.setattr(scanner.db, "get_watchlist", lambda: deepcopy(watchlist))
    monkeypatch.setattr(
        scanner.db,
        "update_alert_status",
        lambda alert_id, is_triggered, current_value: updates.append(
            (alert_id, is_triggered, current_value)
        ),
    )
    monkeypatch.setattr(
        scanner.db,
        "log_alert_history",
        lambda alert_id, current_value, target: history.append((alert_id, current_value, target)),
    )

    return updates, history


def test_scanner_triggers_absolute_alert_on_false_to_true_transition(monkeypatch):
    watchlist = {
        "AAPL": {
            "name": "Apple Inc.",
            "alerts": [
                {
                    "id": "alert-1",
                    "metric": "pe",
                    "operator": "<",
                    "target": 20.0,
                    "is_active": True,
                    "is_triggered": False,
                    "reference_value": None,
                    "alert_type": "absolute",
                }
            ],
        }
    }
    updates, history = install_fake_scanner_db(monkeypatch, watchlist)
    send_alert = Mock()

    scanner.run_fundamental_scan(
        send_alert,
        market_data_service=FakeMarketDataService({("AAPL", "pe"): 18.0}),
    )

    assert updates == [("alert-1", True, 18.0)]
    assert history == [("alert-1", 18.0, 20.0)]
    send_alert.assert_called_once()
    assert "PE < 20.0" in send_alert.call_args.args[0]


def test_scanner_evaluates_duplicate_same_metric_alerts_by_alert_id(
    monkeypatch,
    duplicate_pe_watchlist,
):
    updates, history = install_fake_scanner_db(monkeypatch, duplicate_pe_watchlist)
    send_alert = Mock()

    scanner.run_fundamental_scan(
        send_alert,
        market_data_service=FakeMarketDataService({("AAPL", "pe"): 45.0}),
    )

    assert updates == [
        ("alert-low", False, 45.0),
        ("alert-high", True, 45.0),
    ]
    assert history == [("alert-high", 45.0, 40.0)]
    send_alert.assert_called_once()
    assert "PE > 40.0" in send_alert.call_args.args[0]


def test_scanner_triggers_relative_alert_using_reference_value(monkeypatch):
    watchlist = {
        "AAPL": {
            "name": "Apple Inc.",
            "alerts": [
                {
                    "id": "relative-1",
                    "metric": "price",
                    "operator": ">=",
                    "target": 10.0,
                    "is_active": True,
                    "is_triggered": False,
                    "reference_value": 100.0,
                    "alert_type": "relative",
                }
            ],
        }
    }
    updates, history = install_fake_scanner_db(monkeypatch, watchlist)
    send_alert = Mock()

    scanner.run_fundamental_scan(
        send_alert,
        market_data_service=FakeMarketDataService({("AAPL", "price"): 115.0}),
    )

    assert updates == [("relative-1", True, 115.0)]
    assert history == [("relative-1", 115.0, 10.0)]
    send_alert.assert_called_once()
    message = send_alert.call_args.args[0]
    assert "PRICE changed by >= 10.0%" in message
    assert "Diff: 15.00%" in message


def test_scanner_does_not_realert_when_alert_is_already_triggered(monkeypatch):
    watchlist = {
        "AAPL": {
            "name": "Apple Inc.",
            "alerts": [
                {
                    "id": "alert-1",
                    "metric": "pe",
                    "operator": "<",
                    "target": 20.0,
                    "is_active": True,
                    "is_triggered": True,
                    "reference_value": None,
                    "alert_type": "absolute",
                }
            ],
        }
    }
    updates, history = install_fake_scanner_db(monkeypatch, watchlist)
    send_alert = Mock()

    scanner.run_fundamental_scan(
        send_alert,
        market_data_service=FakeMarketDataService({("AAPL", "pe"): 18.0}),
    )

    assert updates == [("alert-1", True, 18.0)]
    assert history == []
    send_alert.assert_not_called()


def test_scanner_clears_triggered_state_without_logging_transition(monkeypatch):
    watchlist = {
        "AAPL": {
            "name": "Apple Inc.",
            "alerts": [
                {
                    "id": "alert-1",
                    "metric": "pe",
                    "operator": "<",
                    "target": 20.0,
                    "is_active": True,
                    "is_triggered": True,
                    "reference_value": None,
                    "alert_type": "absolute",
                }
            ],
        }
    }
    updates, history = install_fake_scanner_db(monkeypatch, watchlist)
    send_alert = Mock()

    scanner.run_fundamental_scan(
        send_alert,
        market_data_service=FakeMarketDataService({("AAPL", "pe"): 25.0}),
    )

    assert updates == [("alert-1", False, 25.0)]
    assert history == []
    send_alert.assert_not_called()


def test_scanner_skips_inactive_alerts_and_missing_provider_values(monkeypatch):
    watchlist = {
        "AAPL": {
            "name": "Apple Inc.",
            "alerts": [
                {
                    "id": "inactive",
                    "metric": "pe",
                    "operator": "<",
                    "target": 20.0,
                    "is_active": False,
                    "is_triggered": False,
                    "reference_value": None,
                    "alert_type": "absolute",
                },
                {
                    "id": "missing-value",
                    "metric": "price",
                    "operator": ">",
                    "target": 200.0,
                    "is_active": True,
                    "is_triggered": False,
                    "reference_value": None,
                    "alert_type": "absolute",
                },
            ],
        }
    }
    updates, history = install_fake_scanner_db(monkeypatch, watchlist)
    send_alert = Mock()
    service = FakeMarketDataService(values={("AAPL", "price"): None})

    scanner.run_fundamental_scan(send_alert, market_data_service=service)

    assert service.calls == [("AAPL", "price")]
    assert updates == []
    assert history == []
    send_alert.assert_not_called()
