# yfinance usage in FundamenTracker

This project uses `yfinance` via `yf.Ticker(...).info` for ticker metadata and alert metric evaluation.

## Fields currently used

### 1) Watchlist metadata
- `shortName`
  - Used when adding a ticker to store a human-readable company name.
  - Fetched in `fetch_company_name()`.

### 2) Alert metrics (via `METRICS_MAP`)
- `trailingPE` (`pe`)
- `forwardPE` (`fpe`)
- `priceToBook` (`pb`)
- `enterpriseToEbitda` (`evebitda`)
- `returnOnEquity` (`roe`)
- `currentPrice` (`price`)

These are used for:
- `/list` and `/alerts` views (on-demand fetch per alert metric)
- scheduled scanner evaluation for trigger conditions

## Runtime pattern

```python
import yfinance as yf

info = yf.Ticker("AAPL").info
name = info.get("shortName", "AAPL")
trailing_pe = info.get("trailingPE")
current_price = info.get("currentPrice")
```

## Practical notes

- `info` is best-effort and may be incomplete for some symbols/markets.
- Any configured metric can be missing (`None`); the app skips evaluation for that alert in that run.
- Exchange suffixes matter (`.L`, `.PA`, `.TO`, etc.).
- Values are fetched live; there is no local quote cache.

## Extension guidance

To add a new alert metric:
1. Add a key mapping in `src/config.py` (`METRICS_MAP`).
2. No state schema change is required; existing `alerts[]` entries are generic.
3. The metric becomes available automatically in `/help`, `/add`, `/list`, `/alerts`, and scanner evaluation.
