from __future__ import annotations

from copy import deepcopy

from fastapi.testclient import TestClient

import api as api_module
from api import app


AUTH_HEADER = {"Authorization": "Bearer test-token"}


def test_add_tag_to_ticker(monkeypatch):
    monkeypatch.setenv("API_AUTH_TOKEN", "test-token")
    monkeypatch.delenv("READONLY_PUBLIC", raising=False)

    state = {
        "AAPL": {
            "name": "Apple Inc.",
            "status": "watching",
            "priority": "medium",
            "notes": None,
            "thesis": None,
            "target_action": None,
            "tags": [],
            "alerts": [],
        }
    }

    def fake_add_tag_to_ticker(symbol, name, color=None):
        tag = {"id": "tag-1", "name": name, "color": color}
        state[symbol]["tags"].append(tag)
        return deepcopy(tag)

    monkeypatch.setattr(api_module.db, "get_watchlist", lambda: deepcopy(state))
    monkeypatch.setattr(api_module.db, "add_tag_to_ticker", fake_add_tag_to_ticker)

    client = TestClient(app)
    response = client.post("/watchlist/aapl/tags", headers=AUTH_HEADER, json={"name": "Core"})

    assert response.status_code == 200
    assert response.json() == {"id": "tag-1", "name": "core", "color": None}
    assert state["AAPL"]["tags"] == [{"id": "tag-1", "name": "core", "color": None}]


def test_remove_tag_from_ticker(monkeypatch):
    monkeypatch.setenv("API_AUTH_TOKEN", "test-token")
    monkeypatch.delenv("READONLY_PUBLIC", raising=False)

    state = {
        "AAPL": {
            "name": "Apple Inc.",
            "status": "watching",
            "priority": "medium",
            "notes": None,
            "thesis": None,
            "target_action": None,
            "tags": [{"id": "tag-1", "name": "core", "color": None}],
            "alerts": [],
        }
    }

    def fake_remove_tag_from_ticker(symbol, tag_name_or_id):
        before = len(state[symbol]["tags"])
        state[symbol]["tags"] = [
            tag
            for tag in state[symbol]["tags"]
            if tag["id"] != tag_name_or_id and tag["name"] != tag_name_or_id
        ]
        return len(state[symbol]["tags"]) != before

    monkeypatch.setattr(api_module.db, "get_watchlist", lambda: deepcopy(state))
    monkeypatch.setattr(api_module.db, "remove_tag_from_ticker", fake_remove_tag_from_ticker)

    client = TestClient(app)
    response = client.delete("/watchlist/AAPL/tags/tag-1", headers=AUTH_HEADER)

    assert response.status_code == 200
    assert response.json() == {"message": "Tag removed"}
    assert state["AAPL"]["tags"] == []


def test_get_watchlist_includes_tags(monkeypatch):
    monkeypatch.setenv("API_AUTH_TOKEN", "test-token")
    monkeypatch.delenv("READONLY_PUBLIC", raising=False)

    watchlist = {
        "AAPL": {
            "name": "Apple Inc.",
            "status": "watching",
            "priority": "medium",
            "notes": "Review before earnings.",
            "thesis": None,
            "target_action": None,
            "tags": [{"id": "tag-1", "name": "core", "color": "#2563eb"}],
            "alerts": [],
        }
    }

    monkeypatch.setattr(api_module.db, "get_watchlist", lambda: deepcopy(watchlist))

    client = TestClient(app)
    response = client.get("/watchlist", headers=AUTH_HEADER)

    assert response.status_code == 200
    assert response.json()["AAPL"]["tags"] == [
        {"id": "tag-1", "name": "core", "color": "#2563eb"}
    ]


def test_patch_metadata_updates_status_and_priority(monkeypatch):
    monkeypatch.setenv("API_AUTH_TOKEN", "test-token")
    monkeypatch.delenv("READONLY_PUBLIC", raising=False)

    state = {
        "AAPL": {
            "name": "Apple Inc.",
            "status": "watching",
            "priority": "medium",
            "notes": None,
            "thesis": None,
            "target_action": None,
            "tags": [],
            "alerts": [],
        }
    }

    def fake_update_ticker_metadata(symbol, metadata):
        state[symbol].update(metadata)
        return {"symbol": symbol, **deepcopy(state[symbol])}

    monkeypatch.setattr(api_module.db, "update_ticker_metadata", fake_update_ticker_metadata)

    client = TestClient(app)
    response = client.patch(
        "/watchlist/aapl/metadata",
        headers=AUTH_HEADER,
        json={"status": "researching", "priority": "high"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "researching"
    assert response.json()["priority"] == "high"
    assert state["AAPL"]["status"] == "researching"
    assert state["AAPL"]["priority"] == "high"
