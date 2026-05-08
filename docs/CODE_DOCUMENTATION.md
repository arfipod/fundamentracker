# Code Documentation

This document is a practical code map for the current repository. For broader
flow diagrams and tradeoffs, see [ARCHITECTURE.md](ARCHITECTURE.md).

## Runtime Overview

Active runtime:

1. `api/api.py` creates the FastAPI app exposed as `api.api:app`.
2. `frontend/src/App.tsx` renders the React/Vite frontend.
3. Frontend requests go through `frontend/src/lib/apiClient.ts`.
4. FastAPI route modules in `api/routes/` call service modules in
   `api/services/`.
5. Services call repository implementations in `api/repositories/` and
   market-data code in `api/market_data/`.
6. The scanner in `api/scanner.py` evaluates active alerts and writes alert
   state, history, and Signal Inbox rows through the repository boundary.

Production Docker starts the API through `scripts/start-api.sh`, which can run
local PostgreSQL migrations first when `RUN_MIGRATIONS_ON_START=true`, then
execs `uvicorn api.api:app`.

## Backend Modules

### `api/api.py`

- Configures FastAPI, CORS, bearer-token dependencies, logging, router
  registration, and startup background tasks.
- Creates one repository with `get_repository()` and one `MarketDataService`.
- Starts periodic scanning and Telegram polling on startup.
- Public health and read endpoints are defined by routers, not directly in this
  file.

### `api/routes/`

Active route modules:

- `health.py`: `GET /health/live`, `GET /health/ready`.
- `watchlist.py`: `GET /watchlist`, `POST /add`,
  `DELETE /remove/{ticker}`, and deprecated ticker/metric compatibility routes.
- `alerts.py`: ID-based alert update, soft delete, restore, toggle, deleted
  alert listing, and alert history.
- `scans.py`: manual scan, scan settings, and server time.
- `signals.py`: Signal Inbox listing plus acknowledge and dismiss actions.
- `market.py`: symbol search, provider health, current metrics, history, and
  market overview.
- `valuation.py`: Gemini valuation endpoint.
- `ops.py`: protected operations status snapshot.

Routes should stay thin and delegate behavior to services.

### `api/services/`

Service modules hold behavior that has been split out of routes:

- `watchlist.py`: add/remove watchlist items and alerts, duplicate ticker/metric
  compatibility checks, reference value capture for relative alerts.
- `alerts.py`: ID-based alert mutation, soft-delete/restore behavior, deleted
  alert listing, and history reads.
- `signals.py`: open/all signal reads and acknowledge/dismiss mutations.
- `scans.py`: scan execution, scan interval loop, and Telegram polling startup.
- `market.py`: market-data endpoint behavior.
- `health.py`: health payload formatting.
- `ops.py`: operations status payload.
- `valuation.py`: backend valuation data-pack assembly, Gemini JSON prompt,
  structured response validation, and temporary legacy analysis text.

The valuation service returns structured AI output with label, data quality,
observations, risks, missing data, suggested read-only alerts, sources, and a
disclaimer. It also includes a temporary `analysis` string for older frontend
compatibility. The analysis is limited to the backend data pack and should not
claim historical or sector comparisons unless those data are explicitly present.

### `api/repositories/`

The repository boundary supports two backends:

- `PostgresRepository` in `postgres.py`.
- `SupabaseRestRepository` in `supabase_rest.py`.

`factory.py` selects the backend from `DATABASE_BACKEND`. Production Compose
defaults this to `postgres`; a bare non-Compose API defaults to `supabase_rest`
when `DATABASE_BACKEND` is unset.

The common data shape is defined in `base.py`, including `build_watchlist()`,
which converts ticker and alert rows into the API watchlist response shape.
Repository watchlist and alert-list reads exclude soft-deleted alerts.

### `api/db/`

- `migration_runner.py` applies SQL files from `db/migrations/` to local
  PostgreSQL and records file name/checksum in `schema_migrations`.
- `client.py` is a compatibility wrapper around repository factory functions.

### `api/market_data/`

- `service.py`: `MarketDataService`, snapshot cache lookup/write,
  provider-health updates, stale fallback, and quote/history response shaping.
- `metric_definitions.py`: supported alert/Explorer metrics and yfinance keys.
- `normalizers.py`: symbol, numeric, history, and calculated fundamental helpers.
- `providers/yfinance_provider.py`: default live provider.
- `providers/sec_edgar_provider.py`: SEC company facts provider for selected US
  audited fundamentals. It is implemented and tested but not selected by the
  default live service.

### `api/scanner.py` and `api/alert_evaluator.py`

`scanner.py` loads the watchlist, skips inactive alerts, fetches current values
through `MarketDataService`, evaluates alert conditions, updates alert state,
logs newly triggered alerts, and sends a Telegram message through the provided
callback.

Alert history rows include denormalized ticker, company, metric, operator,
alert type, reference value, current value, provider source, and alert message
when those fields are available during scanning. This preserves investor audit
context independently of later alert soft deletes.

Newly triggered alerts also create `signals` rows with
`signal_type = 'alert_triggered'`. The frontend Signal Inbox reads open signals
from `GET /signals` and hides rows from the open view after acknowledge or
dismiss.

`alert_evaluator.py` owns absolute and relative alert logic. Relative alerts
compare the percentage difference from the stored reference value:

```text
diff_percent = ((current_value / reference_value) - 1) * 100
```

### `api/telegram_service.py`

Optional Telegram integration. It sends alert messages and processes simple bot
commands using the repository-backed watchlist service. Missing Telegram token
or chat ID disables polling.

### Legacy Backend Modules

These modules remain in the repository but are not the active web API path:

- `api/main.py`
- `api/supabase_db.py`
- `api/state.py`
- `api/watchlist.py`

Treat them as legacy/compatibility code unless a task explicitly targets them.

## Frontend Modules

The frontend is a React 19 + Vite + TypeScript app under `frontend/`.

Important files:

- `src/App.tsx`: top-level tabs for Signals, Watchlist, and Explorer. Signals
  is the default tab.
- `src/lib/apiClient.ts`: shared fetch wrapper that adds bearer auth when a
  frontend token is configured.
- `src/hooks/useWatchlist.ts`: watchlist loading, alert add/update/delete/toggle,
  ticker delete, and single-alert undo queue. Single-alert undo restores the
  original alert ID through `POST /alerts/{alert_id}/restore`; ticker delete
  still uses `DELETE /remove/{ticker}` and does not have reliable identity-
  preserving undo yet.
- `src/hooks/useScanSettings.ts`: scan interval, manual scan, and server-time
  offset. Manual scan completion refreshes the watchlist and Signal Inbox.
- `src/components/SignalInbox.tsx`: open signal list with acknowledge, dismiss,
  and refresh controls.
- `src/components/AlertForm.tsx`: add-alert form with ticker autocomplete.
- `src/components/WatchlistSection.tsx`: table/grid views, sorting, and
  backend tag filtering.
- `src/components/TickerRow.tsx` and `TickerCard.tsx`: ticker display,
  inline metric add, persisted tags and metadata, delete controls, and AI
  valuation display.
- `src/components/AlertItem.tsx`: alert rendering, target editing, toggle,
  delete, relative-diff display, and chart toggle.
- `src/components/ExplorerSection.tsx`: ticker/metric lookup outside the
  watchlist.
- `src/components/MetricChart.tsx`: Recharts history chart with period and
  reference-line toggles.

Current tags are backend data returned with `GET /watchlist`, along with basic
ticker metadata such as status and priority.

## Database Schema

Local PostgreSQL bootstrap schema lives in `db/init/001_schema.sql`.
Migrations for existing PostgreSQL databases live in `db/migrations/`.

Current app tables include:

- `tickers`
- `alerts`
- `alert_history`
- `signals`
- `scan_settings`
- `data_providers` (created by bootstrap schema, not actively used by current
  service selection)
- `metric_snapshots`
- `provider_health`
- `schema_migrations` (created by the migration runner)

See [SQL_TABLES.md](SQL_TABLES.md) for schema details.

## Tests And CI

Backend tests are in `tests/` and run with `pytest`. CI uses Python 3.13.

Frontend CI runs `npm ci` and `npm run build` with Node 22. Frontend lint exists
but is intentionally not enforced yet, and there is no `npm test` script.

See [TESTING.md](TESTING.md) for exact commands and known gaps.
