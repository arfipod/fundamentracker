# Data Sources

FundamenTracker uses `yfinance` as the default live provider for quotes, alert
metrics, ticker search, market overview, valuation history, and statement-derived
metrics. A SEC EDGAR provider also supplies selected audited facts for US
issuers through the SEC company-facts XBRL API.

The two sources have different roles:

- yfinance is the broad, low-friction source used by the live watchlist,
  Explorer, scanner, and AI valuation data pack.
- SEC EDGAR is a separate audited-facts endpoint with filing metadata. It does
  not currently replace or arbitrate every yfinance value.

Provider arbitration, provider-disagreement reporting, Alpha Vantage, and FMP
are future work and must not be described as implemented.

## Persistent Metric Cache

Current quotes, metric values, and history payloads are cached in
`metric_snapshots`.

The backend checks for a fresh snapshot before calling a provider. If the
snapshot is expired, `MarketDataService` calls the provider, stores a new
snapshot, and updates `provider_health`. If the provider fails and an older
snapshot exists, that snapshot can be returned with `stale=true`.

Configured TTLs:

```env
MARKET_DATA_TTL_PRICE_SECONDS=300
MARKET_DATA_TTL_QUOTE_SECONDS=300
MARKET_DATA_TTL_FUNDAMENTALS_SECONDS=86400
MARKET_DATA_TTL_STATEMENTS_SECONDS=604800
```

Provider health is exposed through the protected endpoint:

```text
GET /data/providers/health
```

Rows include `provider`, `status`, `last_ok_at`, `last_error_at`, and
`last_error`.

## yfinance Provider

Implementation:

```text
api/market_data/providers/yfinance_provider.py
api/market_data/derived_metrics.py
api/market_data/metric_definitions.py
```

The project pins `yfinance==1.5.2`.

The provider supplies:

- Current price, market capitalization, shares, currency, and exchange metadata,
  preferring `Ticker.fast_info` where appropriate.
- Company and current fundamental fields from `Ticker.info`.
- Real historical valuation measures from
  `Ticker.get_valuation_measures(...)` for market cap, enterprise value, P/E,
  forward P/E, PEG, price/sales, price/book, EV/revenue, and EV/EBITDA.
- TTM and annual statement-derived valuation, cash generation, profitability,
  ROIC, reinvestment, dilution, leverage, growth, buyback, and shareholder-return
  metrics.
- EPS estimate trend and revision-balance metrics.
- Symbol search through Yahoo Finance's search endpoint.

The old valuation-history approximation has been removed. Historical P/E,
forward P/E, P/B, and EV/EBITDA are no longer calculated by combining old prices
with today's EPS, book value, shares, debt, cash, or EBITDA.

The public `GET /metrics/catalog` endpoint indicates:

- display unit and multiplier;
- category and description;
- whether higher values are generally better;
- whether the metric supports alerts;
- whether a reliable historical chart is available;
- source kind, period, and formula where applicable.

Most derived TTM and analyst metrics are intentionally current-only. The
frontend shows their current value but does not draw a fabricated history.

See [yfinance usage](yfinance_capabilities.md) for formulas, source selection,
historical behavior, and limitations.

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

`SEC_USER_AGENT` should be a descriptive, non-secret value for SEC requests. If
it contains personal contact information, keep it in `.env` and do not commit
it.

The provider supports:

- Ticker-to-CIK lookup using SEC `company_tickers.json`, with in-memory caching
  and an optional local JSON cache path.
- `get_company_facts(cik)` for SEC company-facts JSON.
- `extract_us_gaap_metric(symbol, concept, unit)` for a specific `us-gaap`
  concept and unit.
- Basic mapped metrics: revenue, net income, total assets, total liabilities,
  stockholders' equity, operating cash flow, and capex when a supported tag is
  available.

Returned snapshots include `source="sec"` and filing metadata such as CIK,
concept, unit, form, filing date, fiscal year/period, accession number, and
`as_of_date`.

Live API integration:

```text
GET /fundamentals/sec/{ticker}
```

This endpoint is protected by default. It uses `SecEdgarProvider` directly,
returns the supported audited facts available for the ticker, caches each fact
where repository writes are available, and updates SEC provider health.

Response shape:

```json
{
  "ticker": "AAPL",
  "cik": "0000320193",
  "company_name": "Apple Inc.",
  "facts": [
    {
      "metric": "revenue",
      "value": 383285000000.0,
      "unit": "USD",
      "concept": "Revenues",
      "label": "Revenue",
      "fiscal_year": 2023,
      "fiscal_period": "FY",
      "form": "10-K",
      "as_of_date": "2023-09-30",
      "filed_at": "2023-11-03",
      "accession": "0000320193-23-000106",
      "source": "sec"
    }
  ],
  "errors": []
}
```

Missing optional facts appear in `errors` and do not fail the whole response.
A missing SEC ticker mapping, common for non-US issuers, returns an empty facts
array with an explanatory error. Watchlist scans and Explorer metrics continue
to use yfinance unless a separate integration explicitly changes that behavior.

## Source Confidence And Interpretation

Source labels describe provenance, not certainty. Important distinctions:

- `fast_info` and `info` are current Yahoo fields.
- `valuation` is Yahoo's point-in-time valuation time series.
- `statement` is a deterministic FundamenTracker formula over Yahoo statement
  rows.
- `analyst` is consensus-estimate data and receives lower interpretive weight.
- `sec` is an audited reported fact, but it can still be restated and may use a
  company-specific concept that the conservative mapping does not recognize.

A metric can be technically correct yet economically inappropriate for a
particular sector. Banks, insurers, REITs, early-stage companies, and commodity
businesses need sector-aware interpretation.

## SEC EDGAR Limitations

The SEC provider is intentionally conservative:

- It targets US SEC company-facts data and `us-gaap` XBRL concepts.
- It does not cover every possible revenue, cash-flow, equity, liability, or
  capex tag.
- Companies vary in the tags they report.
- It does not yet calculate TTM values, restatement-aware series, or automated
  provider disagreements.
- Capex follows the reported SEC sign and meaning.
- Automated tests use local fixtures and never call SEC EDGAR.

Missing mappings, concepts, and units raise controlled provider errors rather
than returning ambiguous values.
