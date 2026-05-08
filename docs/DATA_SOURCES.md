# Data Sources

FundamenTracker currently uses `yfinance` as the default live provider for
quotes, alert metrics, ticker search, market overview, and historical chart
data. A SEC EDGAR provider module also exists for selected audited US issuer
fundamentals through the SEC company facts XBRL API, but it is not selected by
the default live `MarketDataService`.

Provider arbitration, provider disagreement reporting, Alpha Vantage support,
and FMP support are planned/future work. Do not document them as implemented.

## Persistent Metric Cache

Current quotes, metric values, and history payloads are cached in `metric_snapshots`.

The backend checks for a fresh snapshot before calling the provider. If the snapshot is expired, `MarketDataService` calls the provider, stores a new snapshot, and updates `provider_health`. If the provider fails and an older snapshot exists, the metric endpoint can return that snapshot with `stale=true`.

Configured TTLs:

```env
MARKET_DATA_TTL_PRICE_SECONDS=300
MARKET_DATA_TTL_QUOTE_SECONDS=300
MARKET_DATA_TTL_FUNDAMENTALS_SECONDS=86400
MARKET_DATA_TTL_STATEMENTS_SECONDS=604800
```

Provider health is exposed at:

```text
GET /data/providers/health
```

This endpoint is protected by default and requires `Authorization: Bearer <API_AUTH_TOKEN>` because it exposes operational provider status and recent failure details.

Response rows include `provider`, `status`, `last_ok_at`, `last_error_at`, and `last_error`.

## SEC EDGAR Provider

Implementation:

```text
api/market_data/providers/sec_edgar_provider.py
```

Configuration:

```env
SEC_USER_AGENT=FundamenTracker contact@example.com
SEC_RATE_LIMIT_SECONDS=0.2
SEC_TICKER_CACHE_PATH=
```

`SEC_USER_AGENT` should be a descriptive, non-secret value for SEC requests. If it contains personal contact information, keep it in `.env` and do not commit it.

The provider supports:

- ticker to CIK lookup using SEC `company_tickers.json`, with in-memory caching and an optional local JSON cache path.
- `get_company_facts(cik)` for SEC company facts JSON.
- `extract_us_gaap_metric(symbol, concept, unit)` for a specific `us-gaap` concept and unit.
- basic mapped metrics: `revenue`, `net_income`, `total_assets`, `total_liabilities`, `stockholders_equity`, `operating_cash_flow`, and `capex` when a supported tag exists.

Returned metric snapshots include `source="sec"` plus SEC filing metadata such as CIK, concept, unit, form, filing date, fiscal year/period, accession number, and `as_of_date`.

Current integration limitation: the live API's default `MarketDataService`
constructs `YFinanceProvider()`. The SEC provider is available for direct use,
tests, and future service wiring, but current alert scans and Explorer calls do
not automatically prefer SEC data for audited fundamentals.

## yfinance Provider

Implementation:

```text
api/market_data/providers/yfinance_provider.py
```

The yfinance provider currently supplies:

- `get_quote(symbol)` from `yf.Ticker(symbol).info`.
- `get_metric(symbol, metric)` for the metric catalog in
  `api/market_data/metric_definitions.py`.
- `get_price_history(symbol, period)` and normalized price-history points.
- best-effort metric histories for valuation ratios, profitability metrics,
  leverage metrics, dividend yield, and payout ratio.
- symbol search through Yahoo Finance's search endpoint.

Some historical fundamental charts are derived from current yfinance fields or
quarterly statements. They are useful for context, but they are not a complete
audited point-in-time fundamentals database.

See [yfinance usage](yfinance_capabilities.md) for the exact current fields and
limitations.

## SEC EDGAR Limitations

This first SEC provider is intentionally conservative:

- It targets US SEC company facts data and `us-gaap` XBRL concepts.
- It does not cover every possible revenue, cash-flow, equity, liability, or capex tag.
- Companies vary in the tags they report, and some values may be absent even when the company filed XBRL data.
- Values are selected from reported facts by filing metadata; the provider does not yet calculate TTM values, restatement-aware series, or provider disagreement checks.
- Capex follows the reported SEC tag sign and meaning; it is not transformed into a free-cash-flow convention.
- Normal unit tests use local JSON fixtures and must not call SEC EDGAR.

Missing ticker mappings, missing concepts, and missing units raise controlled SEC provider errors instead of returning ambiguous values.
