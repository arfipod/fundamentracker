from __future__ import annotations

import json
from pathlib import Path

import pytest

from market_data.providers.sec_edgar_provider import (
    SEC_COMPANY_FACTS_URL,
    SEC_TICKER_URL,
    SecConceptNotFoundError,
    SecEdgarProvider,
    SecTickerNotFoundError,
    SecUnitNotFoundError,
)


FIXTURES_DIR = Path(__file__).parent / "fixtures"


class FakeResponse:
    def __init__(self, payload: dict, ok: bool = True, status_code: int = 200):
        self.payload = payload
        self.ok = ok
        self.status_code = status_code

    def json(self):
        return self.payload


class FakeRequests:
    def __init__(self):
        self.calls: list[dict] = []
        self.tickers = _load_fixture("sec_company_tickers.json")
        self.company_facts = _load_fixture("sec_company_facts_aapl.json")

    def get(self, url: str, *, headers: dict, timeout: int):
        self.calls.append({"url": url, "headers": headers, "timeout": timeout})
        if url == SEC_TICKER_URL:
            return FakeResponse(self.tickers)
        if url == f"{SEC_COMPANY_FACTS_URL}/CIK0000320193.json":
            return FakeResponse(self.company_facts)
        return FakeResponse({}, ok=False, status_code=404)


def test_sec_provider_extracts_us_gaap_metric_with_source():
    provider = SecEdgarProvider(
        user_agent="FundamenTracker tests@example.com",
        requests_client=FakeRequests(),
        min_request_interval_seconds=0,
    )

    revenue = provider.get_metric_snapshot("aapl", "revenue")

    assert revenue["source"] == "sec"
    assert revenue["symbol"] == "AAPL"
    assert revenue["cik"] == "0000320193"
    assert revenue["metric"] == "revenue"
    assert revenue["concept"] == "Revenues"
    assert revenue["unit"] == "USD"
    assert revenue["value"] == 383285000000.0
    assert revenue["as_of_date"] == "2023-09-30"
    assert revenue["filed_at"] == "2023-11-03"
    assert revenue["form"] == "10-K"


def test_sec_provider_supports_basic_sec_metrics():
    provider = SecEdgarProvider(
        user_agent="FundamenTracker tests@example.com",
        requests_client=FakeRequests(),
        min_request_interval_seconds=0,
    )

    metrics = provider.get_basic_metrics("AAPL")

    assert set(metrics) == {
        "revenue",
        "net_income",
        "total_assets",
        "total_liabilities",
        "stockholders_equity",
        "operating_cash_flow",
        "capex",
    }
    assert metrics["net_income"]["value"] == 96995000000.0
    assert metrics["capex"]["source"] == "sec"
    assert provider.get_metric("AAPL", "total_assets") == 352583000000.0


def test_sec_provider_uses_configured_user_agent_rate_limit_and_ticker_cache():
    fake_requests = FakeRequests()
    clock_values = iter([100.0, 100.05, 100.25])
    sleep_calls: list[float] = []
    provider = SecEdgarProvider(
        user_agent="FundamenTracker tests@example.com",
        requests_client=fake_requests,
        min_request_interval_seconds=0.2,
        clock=lambda: next(clock_values),
        sleeper=sleep_calls.append,
    )

    assert provider.ticker_to_cik("AAPL") == "0000320193"
    provider.get_company_facts("0000320193")
    assert provider.ticker_to_cik("AAPL") == "0000320193"

    assert len([call for call in fake_requests.calls if call["url"] == SEC_TICKER_URL]) == 1
    assert sleep_calls[0] == pytest.approx(0.15)
    assert all(
        call["headers"]["User-Agent"] == "FundamenTracker tests@example.com"
        for call in fake_requests.calls
    )


def test_sec_provider_returns_controlled_errors_for_missing_cik_concept_or_unit():
    provider = SecEdgarProvider(
        user_agent="FundamenTracker tests@example.com",
        requests_client=FakeRequests(),
        min_request_interval_seconds=0,
    )

    with pytest.raises(SecTickerNotFoundError):
        provider.ticker_to_cik("MSFT")

    with pytest.raises(SecConceptNotFoundError):
        provider.extract_us_gaap_metric("AAPL", "NotARealConcept")

    with pytest.raises(SecUnitNotFoundError):
        provider.extract_us_gaap_metric("AAPL", "Revenues", "shares")


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))
