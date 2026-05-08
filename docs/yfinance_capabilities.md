# yfinance Usage

This document describes current yfinance usage in FundamenTracker. It is not a
complete catalog of everything yfinance can return.

## Active Provider

The default live market-data provider is:

```text
api/market_data/providers/yfinance_provider.py
```

It is used through:

```text
api/market_data/service.py
```

Do not add new direct `yf.Ticker(...)` calls to FastAPI route handlers or
frontend-specific code.

## Current Uses

### Quotes And Ticker Metadata

`YFinanceProvider.get_quote(symbol)` reads `yf.Ticker(symbol).info`, normalizes
the symbol, and adds fallback fields:

- `symbol`
- `name`
- `price`
- `source`

`MarketDataService.get_quote()` caches quote snapshots as metric `quote` in
`metric_snapshots`.

### Alert And Explorer Metrics

Supported live metrics are defined in
`api/market_data/metric_definitions.py`:

| Metric | yfinance key | Display unit |
| --- | --- | --- |
| `pe` | `trailingPE` | ratio |
| `fpe` | `forwardPE` | ratio |
| `pb` | `priceToBook` | ratio |
| `evebitda` | `enterpriseToEbitda` | ratio |
| `roe` | `returnOnEquity` | percent |
| `price` | `currentPrice` | currency |
| `roic` | calculated fallback from quarterly statements when possible | percent |
| `dividendyield` | `dividendYield` | percent |
| `payoutratio` | `payoutRatio` | percent |
| `debttoequity` | `debtToEquity` | ratio |
| `profitmargins` | `profitMargins` | percent |
| `operatingmargins` | `operatingMargins` | percent |

Percent metrics are normalized by multiplying the yfinance ratio by `100` before
returning or storing through `MarketDataService`.

### Historical Data

`YFinanceProvider.get_metric_history(symbol, metric, period)` supports:

- price history from `Ticker.history(period=...)`.
- PE/FPE/PB ratio histories derived from historical close price and current
  EPS/book-value fields.
- EV/EBITDA history derived from historical close price plus current share,
  debt, cash, and EBITDA fields.
- ROE, ROIC, debt-to-equity, profit margins, and operating margins from
  quarterly income statement and balance sheet data when available.
- dividend yield from historical close price and current dividend rate.
- payout ratio as a repeated current value across the historical price index.

This is best-effort chart support. Many fundamental histories are approximations
from current yfinance fields or quarterly statement data, not audited
point-in-time historical ratios.

### Search And Market Overview

Ticker search calls Yahoo Finance's search endpoint with `requests`.
Market overview is implemented in `api/services/market.py` through the
market-data service.

## Cache And Failure Behavior

`MarketDataService` checks `metric_snapshots` before calling yfinance. Fresh
snapshots are returned directly. On provider failure, stale snapshots can be
returned when available and marked with `stale=true`.

Provider health is updated in `provider_health`.

## Practical Limitations

- yfinance data is best-effort and can be missing, delayed, restated, or
  inconsistent across symbols and markets.
- Exchange suffixes matter, for example `.L`, `.PA`, or `.TO`.
- Missing metrics return `None` or raise a controlled error depending on the
  call path.
- Alert scans skip an alert when the current metric value cannot be fetched.
- The app does not currently compare yfinance values against another live
  provider before selecting a value.

## Extension Guidance

To add a new yfinance-backed alert metric:

1. Add a `MetricDefinition` in `api/market_data/metric_definitions.py`.
2. Add or update provider logic in
   `api/market_data/providers/yfinance_provider.py` if the value cannot be read
   directly from `Ticker.info`.
3. Update frontend metric selectors in `AlertForm.tsx`, `TickerRow.tsx`,
   `TickerCard.tsx`, and `ExplorerSection.tsx`.
4. Add backend tests with fake provider data. Do not call live yfinance in tests.
5. Update README and data-source docs.
