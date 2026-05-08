from __future__ import annotations

import json

import pytest

import api as api_module  # noqa: F401 - importing api registers local module paths for service imports.
from schemas.valuation import ValuationResponse
from services import valuation


class FakeMarketDataService:
    def __init__(self):
        self.quote_calls: list[str] = []
        self.metric_calls: list[tuple[str, str]] = []

    def get_quote(self, symbol):
        self.quote_calls.append(symbol)
        return {
            "symbol": symbol,
            "longName": "Example Co",
            "price": 101.5,
            "currency": "USD",
            "sector": "Technology",
            "industry": "Software",
            "source": "fake-provider",
            "as_of_date": "2026-05-08",
            "fetched_at": "2026-05-08T12:00:00+00:00",
            "stale": False,
        }

    def get_metric_snapshot(self, symbol, metric):
        self.metric_calls.append((symbol, metric))
        values = {
            "pe": 18.0,
            "fpe": 17.0,
            "pb": 4.2,
            "evebitda": 12.5,
            "roe": 23.0,
            "roic": None,
            "profitmargins": 21.0,
            "operatingmargins": 29.0,
            "debttoequity": 0.8,
            "dividendyield": 0.7,
            "payoutratio": 18.0,
        }
        return {
            "metric": metric,
            "value": values[metric],
            "unit": "ratio",
            "source": "fake-provider",
            "as_of_date": "2026-05-08",
            "fetched_at": "2026-05-08T12:00:00+00:00",
            "stale": False,
        }


def test_valuation_data_pack_uses_market_data_service_without_live_provider():
    service = FakeMarketDataService()

    data_pack = valuation.build_valuation_data_pack(service, "aapl")

    assert service.quote_calls == ["AAPL"]
    assert ("AAPL", "pe") in service.metric_calls
    assert ("AAPL", "roe") in service.metric_calls
    assert data_pack["quote"]["company_name"] == "Example Co"
    assert {metric["category"] for metric in data_pack["metrics"]} == {
        "Leverage",
        "Profitability",
        "Shareholder Return",
        "Valuation",
    }
    assert "Return on Invested Capital value is unavailable" in data_pack["backend_missing_data"]
    assert any(source["metric"] == "quote" for source in data_pack["sources"])


def test_missing_gemini_api_key_returns_existing_clear_error(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    service = FakeMarketDataService()

    with pytest.raises(valuation.GeminiApiKeyNotConfiguredError) as exc:
        valuation.generate_ai_valuation(service, "AAPL")

    assert str(exc.value) == "GEMINI_API_KEY not configured. Please set it in your environment."
    assert service.quote_calls == []
    assert service.metric_calls == []


def test_structured_valuation_response_shape_is_validated(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    def fake_gemini_response(api_key, prompt):
        assert api_key == "test-key"
        assert "Use only the JSON data pack below" in prompt
        assert "historical norms" in prompt
        return json.dumps(
            {
                "ticker": "AAPL",
                "company_name": "Example Co",
                "summary": "Current metrics are mixed and do not support a strong valuation call.",
                "valuation_label": "inconclusive",
                "data_quality": "medium",
                "key_observations": ["P/E and profitability are available."],
                "risks": ["No historical norm or peer comparison data was supplied."],
                "missing_data": ["Historical valuation ranges are not supplied."],
                "suggested_alerts": [
                    {
                        "metric": "pe",
                        "operator": "<",
                        "value": 15,
                        "rationale": "Monitor if the valuation ratio falls below a user-defined level.",
                    }
                ],
                "sources": [
                    {
                        "metric": "pe",
                        "source": "fake-provider",
                        "as_of_date": "2026-05-08",
                        "fetched_at": "2026-05-08T12:00:00+00:00",
                        "stale": False,
                    }
                ],
                "disclaimer": valuation.DISCLAIMER,
            }
        )

    monkeypatch.setattr(valuation, "_generate_gemini_response", fake_gemini_response)

    response = valuation.generate_ai_valuation(FakeMarketDataService(), "aapl")
    validated = ValuationResponse.model_validate(response)

    assert validated.ticker == "AAPL"
    assert validated.valuation_label == "inconclusive"
    assert validated.missing_data
    assert validated.disclaimer == valuation.DISCLAIMER
    assert validated.analysis
    assert any(source.metric == "quote" for source in validated.sources)


def test_invalid_structured_valuation_response_is_controlled_error(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(valuation, "_generate_gemini_response", lambda api_key, prompt: "not-json")

    with pytest.raises(valuation.InvalidAIValuationResponseError, match="JSON object"):
        valuation.generate_ai_valuation(FakeMarketDataService(), "AAPL")
