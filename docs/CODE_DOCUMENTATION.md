# Code Documentation — FundamenTracker

## 1) Runtime Overview

FundamenTracker operates as a **full-stack application**:

1. `api/api.py` exposes the core functionality as a REST API using FastAPI.
2. The React (`frontend/`) application acts as the primary client, consuming these APIs.
3. The API layer manages market scanning via `yfinance`, AI valuation via Google's `gemini`, and persists watchlist and alert state using a PostgreSQL Supabase database.

## 2) Module Responsibilities

### `api/api.py`
- Exposes REST endpoints for watchlist retrieval, alert CRUD operations, manual scanning, and historical data retrieval (`/history`).
- Houses the `/ai-valuation` endpoint, which interacts with the Gemini API to produce AI-generated insights.
- Validates payload structures and maintains CORS constraints for the React frontend.

### `api/db/client.py`
- Serves as the interface to Supabase.
- Interacts with `tickers`, `alerts`, `alert_history`, and `scan_settings` relational tables.
- Handles concurrent reads/writes and removes global RAM state dependency.

### `api/config.py`
- `METRICS_MAP`: Maps internal user-facing metric keys (like `pe`, `roic`) to `yfinance` dictionary keys.
- `OPERATORS_MAP`: Maps string operators (e.g., `<`) to Python operator functions.

### `api/scanner.py`
- Queries active alerts from Supabase.
- Retrieves current metric values via `yfinance`.
- For dynamic alerts, compares current values against historical `reference_values`.
- Triggers alerts, logs events to the `alert_history` table, and toggles states.

### `api/telegram_service.py`
- Optional module for Telegram notifications.
- Processes commands (`/add`, `/remove`, `/list`) and mutates state directly.

### `frontend/`
- React + Vite web client using TypeScript.
- **Component Architecture:**
  - `WatchlistSection`: Manages views (Grid vs. Table), controls the tagging ecosystem, and renders the Market Overview widget.
  - `TickerCard` / `TickerRow`: Represent individual tickers in their respective view states, providing UI controls to delete items, toggle charts, and request AI valuations.
  - `InlineChart`: Uses Recharts to visually graph historical metrics (incorporating ±1 Standard Deviation bands).
- Uses standard CSS variables for dark/light styling and responsiveness.

## 3) Alert Transition Logic

For each alert under a ticker:
- Evaluate `OPERATORS_MAP[operator](current_value, target)`.
- If condition is `true` and `is_triggered` was `false` → Send Telegram alert and set `is_triggered = true`.
- If condition is `false` and `is_triggered` was `true` → Set `is_triggered = false`.

This "edge-trigger" model ensures users aren't spammed with identical alerts if a metric simply remains below/above its target.

## 4) Historical Interpolation

When querying `/history` for fundamental metrics (like ROIC, Margins, Debt to Equity), `yfinance` typically only provides data for the most recent 4 quarters.
To prevent drawing misleading flat lines into the distant past, the interpolation logic strictly forward-fills (`ffill`) missing dates within the known range, avoiding infinite backward-filling for "Max" charts.

## 5) Data Dependencies

- **Yahoo Finance (`yfinance`)**: Primary data source for current quotes, market overviews, and historical financial statements.
- **Google GenAI (`google-genai`)**: Consumed by the `/ai-valuation` endpoint to provide NLP-based fundamental analysis.
- **Supabase**: Primary persistent storage for tables.
- **Telegram Bot API**: Alert notification system.

## 6) Extension Points

- **Adding Metrics:** Add the key mapping in `api/config.py` (`METRICS_MAP`) and ensure it's handled in `_get_historical_fundamental` (in `api.py`) if history is supported.
- **Adding UI Fields:** Map the new data into the React UI components (`TickerCard` / `TickerRow`).
