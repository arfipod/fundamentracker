# Data Sources

FundamenTracker currently uses `yfinance` for live quotes and alert-oriented market metrics. A basic SEC EDGAR provider also exists for audited US issuer fundamentals exposed through the SEC company facts XBRL API.

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

## Limitations

This first SEC provider is intentionally conservative:

- It targets US SEC company facts data and `us-gaap` XBRL concepts.
- It does not cover every possible revenue, cash-flow, equity, liability, or capex tag.
- Companies vary in the tags they report, and some values may be absent even when the company filed XBRL data.
- Values are selected from reported facts by filing metadata; the provider does not yet calculate TTM values, restatement-aware series, or provider disagreement checks.
- Capex follows the reported SEC tag sign and meaning; it is not transformed into a free-cash-flow convention.
- Normal unit tests use local JSON fixtures and must not call SEC EDGAR.

Missing ticker mappings, missing concepts, and missing units raise controlled SEC provider errors instead of returning ambiguous values.
