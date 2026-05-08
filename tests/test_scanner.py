from __future__ import annotations

from copy import deepcopy
from unittest.mock import Mock

import scanner


EMPTY_SNAPSHOT_METADATA = {
    "source": None,
    "as_of_date": None,
    "fetched_at": None,
    "expires_at": None,
    "stale": False,
    "confidence": None,
}


class FakeMarketDataService:
    def __init__(self, values=None, errors=None):
        self.values = values or {}
        self.errors = errors or {}
        self.calls = []

    def get_metric_snapshot(self, symbol, metric):
        self.calls.append((symbol, metric))
        key = (symbol, metric)
        if key in self.errors:
            raise self.errors[key]
        value = self.values.get(key)
        if isinstance(value, dict):
            return value
        return {"value": value}


class FakeScannerRepository:
    def __init__(self, watchlist, updates, history):
        self.watchlist = watchlist
        self.updates = updates
        self.history = history
        self.history_metadata = []

    def get_watchlist(self):
        return deepcopy(self.watchlist)

    def update_alert_status(self, alert_id, is_triggered, current_value, current_metadata=None):
        self.updates.append((alert_id, is_triggered, current_value, current_metadata or {}))

    def log_alert_history(self, alert_id, current_value, target, metadata=None):
        self.history.append((alert_id, current_value, target))
        self.history_metadata.append(metadata or {})


def install_fake_scanner_db(watchlist):
    updates = []
    history = []
    repository = FakeScannerRepository(watchlist, updates, history)
    return repository, updates, history


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
    repository, updates, history = install_fake_scanner_db(watchlist)
    send_alert = Mock()

    scanner.run_fundamental_scan(
        send_alert,
        market_data_service=FakeMarketDataService({("AAPL", "pe"): 18.0}),
        repository=repository,
    )

    assert updates == [("alert-1", True, 18.0, EMPTY_SNAPSHOT_METADATA)]
    assert history == [("alert-1", 18.0, 20.0)]
    send_alert.assert_called_once()
    assert "PE < 20.0" in send_alert.call_args.args[0]


def test_scanner_evaluates_duplicate_same_metric_alerts_by_alert_id(
    monkeypatch,
    duplicate_pe_watchlist,
):
    repository, updates, history = install_fake_scanner_db(duplicate_pe_watchlist)
    send_alert = Mock()

    scanner.run_fundamental_scan(
        send_alert,
        market_data_service=FakeMarketDataService({("AAPL", "pe"): 45.0}),
        repository=repository,
    )

    assert updates == [
        ("alert-low", False, 45.0, EMPTY_SNAPSHOT_METADATA),
        ("alert-high", True, 45.0, EMPTY_SNAPSHOT_METADATA),
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
    repository, updates, history = install_fake_scanner_db(watchlist)
    send_alert = Mock()

    scanner.run_fundamental_scan(
        send_alert,
        market_data_service=FakeMarketDataService({("AAPL", "price"): 115.0}),
        repository=repository,
    )

    assert updates == [("relative-1", True, 115.0, EMPTY_SNAPSHOT_METADATA)]
    assert history == [("relative-1", 115.0, 10.0)]
    assert repository.history_metadata == [
        {
            "ticker_symbol": "AAPL",
            "company_name": "Apple Inc.",
            "metric": "price",
            "operator": ">=",
            "alert_type": "relative",
            "reference_value": 100.0,
            "current_value": 115.0,
            "source": None,
            "as_of_date": None,
            "fetched_at": None,
            "message": send_alert.call_args.args[0],
        }
    ]
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
    repository, updates, history = install_fake_scanner_db(watchlist)
    send_alert = Mock()

    scanner.run_fundamental_scan(
        send_alert,
        market_data_service=FakeMarketDataService({("AAPL", "pe"): 18.0}),
        repository=repository,
    )

    assert updates == [("alert-1", True, 18.0, EMPTY_SNAPSHOT_METADATA)]
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
    repository, updates, history = install_fake_scanner_db(watchlist)
    send_alert = Mock()

    scanner.run_fundamental_scan(
        send_alert,
        market_data_service=FakeMarketDataService({("AAPL", "pe"): 25.0}),
        repository=repository,
    )

    assert updates == [("alert-1", False, 25.0, EMPTY_SNAPSHOT_METADATA)]
    assert history == []
    send_alert.assert_not_called()


def test_scanner_stores_current_metric_snapshot_metadata(monkeypatch):
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
    repository, updates, history = install_fake_scanner_db(watchlist)
    send_alert = Mock()
    snapshot = {
        "value": 18.0,
        "source": "yfinance",
        "as_of_date": "2026-05-08",
        "fetched_at": "2026-05-08T12:00:00+00:00",
        "expires_at": "2026-05-08T12:05:00+00:00",
        "stale": True,
        "confidence": 0.8,
    }

    scanner.run_fundamental_scan(
        send_alert,
        market_data_service=FakeMarketDataService({("AAPL", "pe"): snapshot}),
        repository=repository,
    )

    expected_metadata = {
        "source": "yfinance",
        "as_of_date": "2026-05-08",
        "fetched_at": "2026-05-08T12:00:00+00:00",
        "expires_at": "2026-05-08T12:05:00+00:00",
        "stale": True,
        "confidence": 0.8,
    }
    assert updates == [("alert-1", True, 18.0, expected_metadata)]
    assert history == [("alert-1", 18.0, 20.0)]
    assert repository.history_metadata[0]["source"] == "yfinance"
    assert repository.history_metadata[0]["as_of_date"] == "2026-05-08"
    assert repository.history_metadata[0]["fetched_at"] == "2026-05-08T12:00:00+00:00"


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
    repository, updates, history = install_fake_scanner_db(watchlist)
    send_alert = Mock()
    service = FakeMarketDataService(values={("AAPL", "price"): None})

    scanner.run_fundamental_scan(send_alert, market_data_service=service, repository=repository)

    assert service.calls == [("AAPL", "price")]
    assert updates == []
    assert history == []
    send_alert.assert_not_called()
