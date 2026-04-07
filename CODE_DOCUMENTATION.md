# Code Documentation — FundamenTracker

## 1) Runtime overview

`src/main.py` is the only entrypoint and supports 3 execution paths:

1. `--test` path: sends a Telegram connectivity message and exits.
2. `--cli` path: handles one-off add/remove actions, persists to JSONBin, exits.
3. default path: processes Telegram updates, scans watchlist fundamentals, persists state.

## 2) Module responsibilities

### `src/main.py`
- Parses arguments.
- Loads and validates persisted state.
- Delegates Telegram command processing.
- Delegates fundamental scanning.
- Persists resulting state.

### `src/state.py`
- `default_state()` returns the canonical empty state object.
- `ensure_state_shape(state)` guards against malformed external payloads.

### `src/jsonbin.py`
- Reads/writes the state record from JSONBin REST API.
- Falls back to `default_state()` on read failures.

### `src/watchlist.py`
- `parse_trigger(value)` validates positive numeric threshold.
- `fetch_company_name(ticker)` retrieves the company short name from yfinance.
- `fetch_current_pe(ticker)` retrieves the current trailing PE from yfinance; returns `None` on failure.
- `add_ticker` and `remove_ticker` mutate watchlist entries.
- `format_watchlist_message` renders the current watchlist with current PE values for Telegram.
- `format_alerts_message` renders alert configuration with current PE values and trigger status for Telegram.

### `src/telegram_service.py`
- `send_message` and `get_updates` wrap Telegram HTTP calls.
- `process_telegram_commands` parses bot commands and mutates state.
- Supports unknown-command response with inline help text.

### `src/scanner.py`
- Iterates current watchlist.
- Retrieves `trailingPE` and `currentPrice` from `yfinance`.
- Sends alert only when crossing below trigger.
- Resets `last_pe_alert` when PE returns above/equal trigger.

## 3) Alert transition logic

For each ticker:

- If `pe < trigger` and `last_pe_alert` is `None` (or `>= trigger`) → send alert and set `last_pe_alert = pe`.
- If `pe >= trigger` and `last_pe_alert` is not `None` → clear `last_pe_alert`.

This is a simple edge-trigger model that avoids duplicate alerts while PE stays under threshold.

## 4) Data dependencies

- **Yahoo Finance (`yfinance`)**: source for `shortName`, `trailingPE`, and `currentPrice`.
- **JSONBin**: persistence of bot state between runs.
- **Telegram Bot API**: input (commands) and output (alerts).

## 5) Operational behavior

- If watchlist is empty after command processing, program exits early after saving state.
- Network/API failures are handled defensively; failures for one ticker do not stop the full run.

## 6) Display features

- `/list` and `/alerts` commands now show real-time current PE values alongside the configured trigger thresholds.
- Current PE values are fetched live from yfinance when the user requests them, not cached in state.
- If current PE fetch fails, the line is displayed without the current value.

## 7) Extension points

- Add new Telegram commands in `process_telegram_commands`.
- Add new scanner conditions in `run_fundamental_scan`.
- Add schema fields in `default_state` and preserve via `ensure_state_shape`.
