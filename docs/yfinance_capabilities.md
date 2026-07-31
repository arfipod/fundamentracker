# yfinance Usage

This document describes the yfinance integration used by FundamenTracker. The
provider is intentionally explicit about where each value comes from and whether
a reliable historical series is available.

## Active Provider

The default live market-data provider is:

```text
api/market_data/providers/yfinance_provider.py
```

It is consumed through `api/market_data/service.py`. FastAPI routes and frontend
components must not call `yf.Ticker(...)` directly.

The pinned version is:

```text
yfinance==1.5.2
```

This version exposes valuation measures through Yahoo's fundamentals time-series
endpoint and supports TTM income/cash-flow statements. yfinance is an unofficial
Yahoo Finance client: fields can be missing, delayed, restated, or inconsistent
between securities and markets.

## Source Kinds

Every catalog metric declares a `source_kind` so the UI and future provider
arbitration can distinguish how it is produced:

| Source kind | Meaning |
| --- | --- |
| `fast_info` | Lightweight current quote fields such as price and market cap. |
| `info` | Flattened Yahoo `financialData`, `defaultKeyStatistics`, and related quote-summary fields. |
| `valuation` | Current and point-in-time valuation measures from `Ticker.get_valuation_measures()`. |
| `statement` | Deterministic calculation from TTM statements and the latest/average balance sheet. |
| `valuation_context` | Current valuation compared with available five-year valuation observations. |
| `growth` | Yahoo current YoY growth field with annual-statement fallback. |
| `analyst` | EPS trend or revision data from Yahoo's earnings-trend module. |

The metric catalog also exposes `period` and `formula` when applicable.

## Quotes And Size

`YFinanceProvider.get_quote(symbol)` combines:

- `Ticker.fast_info` for current price, market capitalization, shares, currency,
  exchange, and timezone when available.
- `Ticker.info` for company name, sector, industry, and fallback quote fields.

`fast_info` is preferred for small quote fields because it avoids loading more
quote-summary data than necessary. `Ticker.info` remains a best-effort fallback.

## Real Valuation History

For yfinance 1.5.2, FundamenTracker uses:

```python
ticker.get_valuation_measures(freq="quarterly", periods=None)
```

Yahoo returns a `Current` column plus dated observations for:

- Market capitalization.
- Enterprise value.
- Trailing P/E.
- Forward P/E.
- Expected five-year PEG.
- Price/sales.
- Price/book.
- EV/revenue.
- EV/EBITDA.

The provider requests monthly observations for periods up to one year,
quarterly observations for two- and five-year charts, and yearly observations
for longer charts.

This replaces the old approximation that divided every historical share price
by today's EPS/book value, or combined historical price with today's shares,
debt, cash, and EBITDA. Those old series were not point-in-time valuation
histories and could materially misstate how expensive a company was in the past.

Five-year valuation-context metrics are calculated from the real observations:

```text
discount_to_median = current_multiple / median_multiple - 1
percentile = observations_at_or_below_current / observation_count
```

At least three valid, positive historical observations are required. A negative
`discount_to_median` means the current multiple is below its historical median.
Historical-relative valuation is context, not an intrinsic-value estimate.

## TTM Statement Data

The provider builds a reusable fundamental data pack from:

```python
ticker.ttm_income_stmt
ticker.ttm_cash_flow
ticker.quarterly_balance_sheet
ticker.income_stmt
ticker.cash_flow
ticker.balance_sheet
```

The TTM income statement and cash-flow statement supply trailing flow values.
The quarterly balance sheet supplies current and prior-year balance values for
average capital calculations. Annual statements supply YoY growth and margin
changes.

Missing lines remain missing. Calculations must not silently replace an absent
statement item with zero unless zero is economically appropriate within a
formula, such as absent debt in an enterprise-value fallback after all debt
aliases have been checked.

## Derived Valuation And Cash Metrics

The provider calculates the following current metrics when their required inputs
are available:

| Metric | Formula |
| --- | --- |
| `normalized_pe` | price / Yahoo normalized diluted EPS |
| `ev_to_ebit_ttm` | enterprise value / TTM EBIT |
| `price_to_fcf_ttm` | market cap / positive TTM FCF |
| `fcf_yield_ttm` | TTM FCF / market cap |
| `earnings_yield_ttm` | TTM common net income / market cap |
| `owner_earnings_yield_ttm` | (TTM FCF - TTM stock-based compensation) / market cap |

`price_to_fcf_ttm` is not returned when FCF is zero or negative. Yield metrics
can be negative, which is useful information.

The owner-earnings metric is a deliberately conservative application-specific
proxy, not a GAAP measure and not a claim that all stock-based compensation must
be subtracted from every valuation model.

## Profitability And Quality

Important calculated metrics include:

- `roe`: TTM net income / average current and prior-year equity.
- `roic`: TTM EBIT after an effective tax rate / average invested capital.
- `gross_margin_ttm`, `profitmargins`, and `operatingmargins`.
- `fcf_margin_ttm`.
- `cfo_to_net_income_ttm` and `fcf_to_net_income_ttm`.
- `interest_coverage_ttm`.
- `normalized_eps_gap`.

ROIC prefers Yahoo's reported `Invested Capital`. If it is unavailable, the
fallback is debt plus equity less cash and short-term investments. The effective
tax rate uses `Tax Rate For Calcs`, then tax provision / pretax income, and
finally a 21% fallback when no defensible rate is available.

## Reinvestment, Dilution, Leverage, And Capital Allocation

Current statement-derived metrics include:

- Capex/revenue.
- Stock-based compensation/revenue and SBC/FCF.
- R&D/revenue.
- Diluted-share growth.
- Net debt/EBITDA.
- Net cash/market cap.
- Gross and net buyback yield.
- Shareholder yield including cash dividends.

Cash-flow statement signs vary by field. Repurchases, dividends, and capex use
absolute cash outflows where the formula measures economic spending. Gross
buyback yield does not prove that share count fell; `diluted_share_growth_yoy`
should be checked alongside it.

Yahoo's `debtToEquity` current field follows Yahoo's percentage display
convention. FundamenTracker therefore stores and displays, for example, `75` as
75%, not `0.75` as a plain ratio. Its statement-derived history uses the same
convention.

## Growth And Analyst Revisions

Current growth metrics use Yahoo's current fields when available and annual
statements otherwise. Annual growth is not reported when the prior value is zero
or negative because a conventional percentage growth rate would be misleading.
Margin-change metrics are expressed in percentage points.

Analyst metrics use:

```python
ticker.eps_trend
ticker.eps_revisions
```

- `eps_revision_90d` compares the preferred forward EPS estimate with the value
  90 days earlier.
- `eps_revision_balance` is upward minus downward revisions, preferring the
  30-day window and falling back to seven days.

The provider prefers `+1y`, then current-year, next-quarter, and current-quarter
rows. Analyst data has lower confidence than reported statements and must be
used as a secondary signal rather than a valuation anchor.

## Historical Availability

`GET /metrics/catalog` is authoritative for `supported_for_history`.

Reliable history is currently exposed for:

- Price.
- Yahoo valuation-measure series listed above.
- ROE, ROIC, debt/equity, net margin, and operating margin reconstructed from
  quarterly statements using rolling flow windows and point-in-time balances.

Most statement-derived TTM, growth, allocation, and analyst metrics are marked
current-only. The Explorer still displays their current value, description,
period, source kind, and formula, but does not fabricate a chart.

For quarterly profitability history, flow values use up to four reported
quarters. ROE and ROIC use average beginning/ending capital when five balance
observations are available. Early points with shorter reporting history use the
available window and ending capital rather than backfilling nonexistent data.

## Cache And Failure Behavior

`MarketDataService` caches current values and history payloads in
`metric_snapshots`. It returns a fresh snapshot without calling Yahoo; after
expiry it refreshes from the provider. If Yahoo fails and an older snapshot
exists, the stale snapshot can be returned with `stale=true`.

The provider also has short in-process caches for ticker objects, `info`,
statement packs, and valuation tables so one scan does not repeatedly download
the same source payload.

Provider health is stored in `provider_health` and exposed through the protected
`GET /data/providers/health` endpoint.

## Testing Policy

Automated tests must not call Yahoo Finance. Provider and calculator tests use
fake `Ticker` objects and deterministic pandas DataFrames. Tests cover:

- Real valuation-table history rather than synthetic price/current-fundamental
  history.
- TTM ROE and ROIC with average capital.
- Cash-flow, owner-earnings, leverage, reinvestment, growth, buyback, and
  shareholder-yield formulas.
- Five-year median discounts and percentiles.
- Analyst EPS revision calculations.
- Missing and invalid values.

## Practical Limitations

- Yahoo data is not audited by FundamenTracker and can differ from SEC filings.
- TTM and normalized fields depend on Yahoo's mapping and normalization.
- Company-specific reporting labels can be absent even when an equivalent item
  appears in a filing under another taxonomy.
- Financial institutions and some sectors require sector-specific valuation and
  capital definitions; generic EV/EBIT, FCF, debt, and ROIC metrics may not be
  economically appropriate.
- Historical valuation observations can be sparse.
- Exchange suffixes matter, for example `.L`, `.PA`, or `.TO`.
- A low multiple or low historical percentile is an alert for review, not a
  substitute for an intrinsic-value model.

## Extension Guidance

To add another metric:

1. Add a `MetricDefinition` in `api/market_data/metric_definitions.py` with an
   explicit source kind, unit, period, direction, history flag, and formula.
2. Add deterministic calculation logic in `derived_metrics.py`, or a narrow
   provider path when the value is supplied directly by Yahoo.
3. Do not mark history as supported until a real point-in-time series or a
   defensible statement reconstruction exists.
4. Add offline tests for normal, missing, zero, negative, and sector-inapplicable
   inputs.
5. Update this document and the public metric catalog behavior.
