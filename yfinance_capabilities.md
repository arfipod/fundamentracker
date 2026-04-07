# yfinance usage in FundamenTracker

This project currently uses a narrow, stable subset of `yfinance` data from `yf.Ticker(...).info`.

## Fields currently used

### 1) Watchlist metadata
- `shortName`
  - Used when adding a ticker to store a human-readable company name.
  - Fetched in `fetch_company_name()`.

### 2) Display fields
- `trailingPE`
  - Displayed in `/list` and `/alerts` commands for real-time reference.
  - Fetched on-demand in `fetch_current_pe()`.

### 3) Scanner fields
- `trailingPE`
  - Primary signal for alerting during scans.
  - If `None`, the ticker is skipped for that run.
- `currentPrice`
  - Included in Telegram alert payload for context.

## Runtime pattern

```python
import yfinance as yf

# Company metadata (used when adding ticker)
info = yf.Ticker("AAPL").info
name = info.get("shortName", "AAPL")

# Display current PE (used in /list and /alerts commands)
current_pe = info.get("trailingPE")

# Scanner data (used during scans)
pe = info.get("trailingPE")
price = info.get("currentPrice")
```

## Practical notes

- `info` is best-effort and may be incomplete for some symbols.
- `trailingPE` can be missing for negative-earnings companies or sparse datasets.
- Exchange suffixes matter (`.L`, `.PA`, `.TO`, etc.).

## Potential future expansion

If needed, additional fields can be integrated into scanner rules without changing storage shape:
- `forwardPE`
- `priceToBook`
- `enterpriseToEbitda`
- `returnOnEquity`

These are not yet part of current alert logic.
