# Code Documentation — FundamenTracker

## 1) Runtime overview

FundamenTracker now runs primarily as a **full-stack application**:

1. `api/api.py` exposes the core functionality as a REST API using FastAPI.
2. The React frontend consumes those API endpoints as the main user client.
3. The API layer loads, validates, mutates, scans, and persists watchlist state to a PostgreSQL Supabase database.

`api/main.py` remains available as a **secondary/legacy entrypoint** for local CLI-style testing and compatibility workflows.

## 2) Module responsibilities

### `api/api.py`
- Defines FastAPI routes for watchlist retrieval, alert creation/removal, UI toggling, and manual scans.
- Validates request payloads and input constraints.
- Integrates with scanning and database persistence flows.
- Serves as the primary backend interface for the React frontend.

### `api/main.py`
- Legacy CLI/test entrypoint.
- Parses CLI arguments.
- Delegates Telegram command processing.

### `api/config.py`
- `METRICS_MAP`: maps user-facing metric keys to Yahoo Finance keys.
- `OPERATORS_MAP`: maps operator strings to Python operator functions.

### `api/db/client.py`
- Direct REST interface to Supabase.
- Interacts with `tickers`, `alerts`, `alert_history` and `scan_settings` relational tables.
- Eliminates global RAM state dependencies and handles concurrent read/writes.

### `api/watchlist.py`
- Parses numeric target values.
- Retrieves `shortName` and active metrics from yfinance.
- Orchestrates tickers and formatting tools for Telegram messages.

### `api/telegram_service.py`
- `send_message` and `get_updates` wrap Telegram HTTP calls.
- `process_telegram_commands` parses commands and mutates state via DB client.
- Supports default `/add TICKER VALUE` behavior (`pe < VALUE`) and explicit 4-argument form.

### `api/scanner.py`
- Queries active alerts from Supabase.
- Retrieves current values from `yfinance`.
- For trailing/dynamic alerts, compares the current value with the historical `reference_value`.
- Triggers alert, logs to `alert_history` table, and updates state in Supabase.

### `frontend/`
- React + Vite web client.
- Primary UX layer for interacting with watchlist and backend operations.

## 3) Alert transition logic

For each alert object under each ticker:

- Evaluate `OPERATORS_MAP[operator](current_value, target)`.
- If condition is `true` and `is_triggered` was `false` → send Telegram alert and set `is_triggered = true`.
- If condition is `false` and `is_triggered` was `true` → set `is_triggered = false`.

This edge-trigger model avoids duplicate notifications while conditions remain true.

## 4) Data model and Architecture

The application no longer uses a globally loaded giant JSON block.
It uses **Supabase Relational Tables** (`tickers`, `alerts`, `alert_history`, `scan_settings`).

## 5) Data dependencies

- **Yahoo Finance (`yfinance`)**: source for `shortName` and configured metric fields.
- **Supabase**: REST endpoints for Database reads/writes (tables).
- **Telegram Bot API**: optional command input and alert output.

## 6) Operational behavior

- All update and scan paths are best-effort and exception-tolerant.
- Per-ticker scan failures are logged and do not stop remaining tickers.
- If watchlist is empty after command processing, the app can persist state and exit early.

## 7) Extension points

- Add new metrics in `api/config.py` (`METRICS_MAP`).
- Add new operators in `api/config.py` (`OPERATORS_MAP`).
- Add new REST endpoints in `api/api.py`.
- Add new Telegram commands in `api/telegram_service.py`.
