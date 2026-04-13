# Code Documentation — FundamenTracker

## 1) Runtime overview

`src/main.py` is the entrypoint and supports 3 execution paths:

1. `--test` path: sends a Telegram connectivity message and exits.
2. `--cli` path: handles one-off actions (`add`, `remove`, `alerts`), persists to JSONBin, exits.
3. default path: processes Telegram updates, scans watchlist fundamentals, persists state.

## 2) Module responsibilities

### `src/main.py`
- Parses CLI arguments.
- Loads and validates persisted state.
- Delegates Telegram command processing.
- Delegates fundamental scanning.
- Persists resulting state.

### `src/config.py`
- `METRICS_MAP`: maps user-facing metric keys to Yahoo Finance keys.
- `OPERATORS_MAP`: maps operator strings to Python operator functions.

### `src/state.py`
- `default_state()` returns the canonical empty state object.
- `ensure_state_shape(state)` guards against malformed external payloads.

### `src/jsonbin.py`
- Reads/writes state to JSONBin REST API.
- Falls back to `default_state()` on read failures.

### `src/watchlist.py`
- `parse_trigger(value)` parses numeric target values.
- `fetch_company_name(ticker)` retrieves `shortName` from yfinance.
- `fetch_metric(ticker, metric_name)` retrieves a mapped metric from yfinance.
- `add_ticker` and `remove_ticker` mutate watchlist entries.
- `format_watchlist_message` renders current watchlist and current metric values.
- `format_alerts_message` renders alert configuration with current trigger status.

### `src/telegram_service.py`
- `send_message` and `get_updates` wrap Telegram HTTP calls.
- `process_telegram_commands` parses commands and mutates state.
- Supports default `/add TICKER VALUE` behavior (`pe < VALUE`) and explicit 4-argument form.

### `src/scanner.py`
- Iterates watchlist and checks each configured alert per ticker.
- Retrieves current values from `yfinance` once per ticker.
- Sends alert only when condition transitions from false to true.
- Resets `is_triggered` when condition becomes false.

### `client.py`
- Optional local interactive menu client for manual inspection and state edits.
- Uses `.env` loading (`python-dotenv`) and the same core modules under `src/`.

## 3) Alert transition logic

For each alert object under each ticker:

- Evaluate `OPERATORS_MAP[operator](current_value, target)`.
- If condition is `true` and `is_triggered` was `false` → send Telegram alert and set `is_triggered = true`.
- If condition is `false` and `is_triggered` was `true` → set `is_triggered = false`.

This edge-trigger model avoids duplicate notifications while conditions remain true.

## 4) Data model

```json
{
  "watchlist": {
    "AAPL": {
      "name": "Apple Inc.",
      "alerts": [
        {
          "metric": "pe",
          "operator": "<",
          "target": 25.0,
          "is_triggered": false
        }
      ]
    }
  },
  "last_update_id": 0
}
```

## 5) Data dependencies

- **Yahoo Finance (`yfinance`)**: source for `shortName` and configured metric fields.
- **JSONBin**: state persistence between runs.
- **Telegram Bot API**: command input and alert output.

## 6) Operational behavior

- All update and scan paths are best-effort and exception-tolerant.
- Per-ticker scan failures are logged and do not stop remaining tickers.
- If watchlist is empty after command processing, the app saves state and exits.

## 7) Extension points

- Add new metrics in `src/config.py` (`METRICS_MAP`).
- Add new operators in `src/config.py` (`OPERATORS_MAP`).
- Add new Telegram commands in `process_telegram_commands`.
- Extend alert payload formatting in `run_fundamental_scan`.
