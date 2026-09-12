# AGENTS.md - FundamenTracker

These instructions are for Codex and other AI agents working in this repository.
Keep changes small, accurate, and grounded in the current code.

## Project Overview

FundamenTracker is a self-hosted fundamental investing tracker for an individual
investor. The active application is a FastAPI backend plus a React/Vite
frontend. It tracks a watchlist, evaluates fundamental/price alerts, stores
state in PostgreSQL, SQLite, or Supabase REST, exposes market-data charts,
optionally sends Telegram notifications, and has a Gemini valuation endpoint.

Long-term goals include stronger provider arbitration, local-first data
ownership, auditable market data, structured AI valuation, and robust Linux host
operation. Do not document or implement those goals as already complete unless
the code proves they are complete.

## Active Architecture

Current active entrypoints:

- Backend web app: `api/api.py`, exposed as `api.api:app`.
- Frontend app: `frontend/src/App.tsx`.
- Shared frontend API helper: `frontend/src/lib/apiClient.ts`.
- Repository factory: `api/repositories/factory.py`.
- PostgreSQL repository: `api/repositories/postgres.py`.
- SQLite repository: `api/repositories/sqlite.py`.
- Supabase REST repository: `api/repositories/supabase_rest.py`.
- Scanner: `api/scanner.py`.
- Market-data service: `api/market_data/service.py`.
- Default market-data provider: `api/market_data/providers/yfinance_provider.py`.
- SEC provider module: `api/market_data/providers/sec_edgar_provider.py`.
- Telegram integration: `api/telegram_service.py`.

Important legacy modules:

- `api/main.py`, `api/supabase_db.py`, `api/state.py`, and `api/watchlist.py`
  are legacy Telegram/CLI-era code. Inspect imports before editing or deleting.
  They are not the active web API entrypoint.
- `experimental/` contains exploratory scripts and should not be treated as
  production code.

Current request flow:

```text
React UI -> apiFetch -> FastAPI route -> service -> repository/provider
```

Current scanner flow:

```text
manual/periodic scan -> api/scanner.py -> MarketDataService -> provider/cache
  -> alert_evaluator -> repository updates -> optional Telegram message
```

## Current Persistence Reality

Three repository backends exist:

- `postgres`
- `sqlite`
- `supabase_rest`

`docker-compose.prod.yml` defaults to `DATABASE_BACKEND=postgres` and starts a
local PostgreSQL service. A bare non-Compose API defaults to `supabase_rest` if
`DATABASE_BACKEND` is unset, because `api/repositories/base.py` normalizes a
missing backend to Supabase REST. Lightweight single-host deployments can select
`DATABASE_BACKEND=sqlite` and must provide `SQLITE_PATH`.

The SQLite schema is in `db/sqlite/001_schema.sql`. The PostgreSQL-to-SQLite
migration implementation is `api/db/postgres_to_sqlite.py`, with the CLI
`scripts/migrate-postgres-to-sqlite.py`. It reads PostgreSQL in a repeatable-read,
read-only transaction, verifies table counts, and refuses to replace an existing
SQLite destination unless explicitly requested.

Business logic should call the repository boundary and must not hardcode one
database backend.

## Safe Working Rules

- Preserve user data. Never delete, reset, recreate, or prune PostgreSQL data,
  SQLite data, Supabase data, alert history, watchlists, or backups unless
  explicitly asked.
- Never commit real secrets. Use `.env.example` and deployment templates with
  dummy values only.
- Be careful with `.env` and `/etc/fundamentracker/fundamentracker.env`: they may
  contain real local secrets. Do not print them in final answers or logs.
- Do not add direct external calls to route handlers. Use services/providers.
- Do not add tests that call Yahoo Finance, SEC EDGAR, Gemini, Telegram,
  Supabase production, Cloudflare, or a real production database.
- Prefer incremental changes over broad rewrites.
- Before deleting or renaming suspicious files, inspect imports, Docker
  entrypoints, tests, docs, and scripts.
- Update docs when changing commands, environment variables, API exposure,
  Docker/systemd behavior, schema, data sources, or testing workflow.
- Keep the Raspberry Pi deployment separate from the generic Docker production
  service. Do not silently replace the existing Docker/PostgreSQL path.

## Configuration And Secrets

Documented configuration lives in `.env.example`. Important variables include:

- `API_AUTH_TOKEN`
- `CORS_ALLOWED_ORIGINS`
- `ALLOW_WILDCARD_CORS`
- `READONLY_PUBLIC`
- `PUBLIC_READY_HEALTH`
- `DATABASE_BACKEND`
- `DATABASE_URL`
- `SQLITE_PATH`
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `RUN_MIGRATIONS_ON_START`
- `MARKET_DATA_TTL_PRICE_SECONDS`
- `MARKET_DATA_TTL_QUOTE_SECONDS`
- `MARKET_DATA_TTL_FUNDAMENTALS_SECONDS`
- `MARKET_DATA_TTL_STATEMENTS_SECONDS`
- `GEMINI_API_KEY`
- `TELEGRAM_TOKEN`
- `TELEGRAM_CHAT_ID`
- `SEC_USER_AGENT`
- `SEC_RATE_LIMIT_SECONDS`
- `SEC_TICKER_CACHE_PATH`
- `VITE_API_URL`
- `VITE_API_AUTH_TOKEN`
- `PUBLIC_API_URL`
- `PUBLIC_HEALTH_URL`
- `WATCHDOG_SERVICES`
- `TUNNEL_TOKEN`

`VITE_API_AUTH_TOKEN` is embedded into browser assets. Do not describe it as
strong auth for a public frontend.

## Coding Conventions

Backend:

- Keep FastAPI routes thin.
- Put application behavior in `api/services/*` where practical.
- Put external market-data calls behind `MarketDataService` and provider
  classes.
- Use typed Pydantic schemas for request bodies and response models when adding
  or changing contracts.
- Use explicit exceptions and logging context. Avoid broad silent `except:`.
- Avoid scattered `os.getenv` in new business logic; prefer configuration helper
  functions or narrow entrypoint reads.

Frontend:

- Use TypeScript types in `frontend/src/types`.
- Use `apiFetch` from `frontend/src/lib/apiClient.ts`.
- Keep loading, error, and empty states explicit.
- Current tags are browser `localStorage` UI state, not backend domain data.
- Do not add repeated raw `fetch` calls when `apiFetch` fits.

Market data:

- Supported live alert metrics are defined in
  `api/market_data/metric_definitions.py`.
- yfinance is the default live provider.
- The SEC provider is implemented and tested, but not selected by default in the
  live API.
- Snapshot cache and provider health are repository-backed through
  `metric_snapshots` and `provider_health`.

AI valuation:

- Current endpoint: `POST /ai-valuation`.
- Current response includes structured fields with `valuation_label`,
  `data_quality`, observations, risks, `missing_data`, read-only
  `suggested_alerts`, `sources`, `disclaimer`, and a temporary legacy
  `analysis` string.
- The analysis is based only on the backend data pack assembled from
  `MarketDataService`; historical norms and sector comparisons are not
  supported unless explicit data for them is added to that pack.

## Alert Rules

- Alert operations should use `alert_id` when editing, deleting, or toggling.
- Duplicate alerts for the same ticker and metric are allowed.
- Deprecated compatibility routes `PUT /update` and
  `DELETE /remove/{ticker}/{metric}` must not mutate ambiguous duplicate
  ticker/metric alerts.
- Relative alerts use:

```text
diff_percent = ((current_value / reference_value) - 1) * 100
```

Then `diff_percent operator target` is evaluated.

## Setup Commands

Backend local setup:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
```

Frontend local setup:

```bash
cd frontend
npm ci
```

Development Compose:

```bash
docker compose -f docker-compose.dev.yml config
docker compose -f docker-compose.dev.yml up --build api frontend
```

Production Compose:

```bash
docker compose -f docker-compose.prod.yml config
docker compose -f docker-compose.prod.yml up -d --build
```

Local PostgreSQL migrations:

```bash
make db-migrate
./scripts/migrate-db.sh --dry-run
```

PostgreSQL-to-SQLite copy:

```bash
python scripts/migrate-postgres-to-sqlite.py \
  --database-url 'postgresql://...' \
  --sqlite-path ./fundamentracker.db
```

Raspberry Pi 1 preflight (non-destructive):

```bash
bash deploy/rpi1/probe-runtime.sh
```

See `docs/RPI1_DEPLOYMENT.md` before installing the native service. ARMv6
compiled-dependency compatibility must be established from the real target; do
not assume x86 CI proves it.

## Validation Commands

Run the most relevant checks for the change.

Backend:

```bash
pytest
```

If `pytest` is not on `PATH`, use the project virtual environment directly:

```bash
.venv/bin/python -m pytest
```

Frontend:

```bash
cd frontend
npm run build
```

Frontend lint exists but is not currently clean:

```bash
cd frontend
npm run lint
```

There is currently no `npm test` script.

Compose:

```bash
docker compose -f docker-compose.dev.yml config
docker compose -f docker-compose.prod.yml config
```

Raspberry deployment shell syntax:

```bash
bash -n deploy/rpi1/probe-runtime.sh
bash -n deploy/rpi1/install-native.sh
bash -n deploy/rpi1/validate-native.sh
```

Docs:

```bash
rg --files -g '*.md'
rg -n 'old-path-or-command' README.md AGENTS.md docs frontend/README.md ISSUES.md
```

## Testing Expectations

- Add or update backend tests for backend behavior changes.
- Use fakes, fixtures, monkeypatching, or local test containers.
- Keep tests deterministic and offline.
- Current focused tests cover health, auth, CORS, alert evaluation, scanner
  transitions, alert ID operations, repository factory behavior, SQLite
  repository parity, PostgreSQL-to-SQLite migration behavior, fake repositories,
  market-data service caching/fallback, normalizers, migration runner, ops
  status, and SEC provider fixtures.
- Frontend build is covered in CI. Frontend unit tests are not yet present.
- Raspberry Pi x86 CI checks are not a substitute for running the ARMv6 runtime
  probe and native validation on the physical target.

## Documentation Rules

- Do not fabricate features.
- Mark planned behavior as planned.
- Mark uncertain behavior honestly.
- Keep command examples copy-pasteable and verify them when feasible.
- When changing public API behavior, environment variables, deployment,
  persistence, data providers, tests, or scripts, update the relevant docs in
  the same change.
- Prefer one authoritative doc per topic and cross-link instead of duplicating
  long sections.

## Files Requiring Extra Care

- `api/api.py`
- `api/repositories/*`
- `api/db/migration_runner.py`
- `api/db/postgres_to_sqlite.py`
- `api/scanner.py`
- `api/alert_evaluator.py`
- `api/telegram_service.py`
- `api/market_data/*`
- `frontend/src/hooks/useWatchlist.ts`
- `frontend/src/hooks/useScanSettings.ts`
- `frontend/src/components/AlertItem.tsx`
- `frontend/src/components/TickerRow.tsx`
- `frontend/src/components/TickerCard.tsx`
- `docker-compose.dev.yml`
- `docker-compose.prod.yml`
- `docker-compose.yml`
- `Dockerfile`
- `frontend/Dockerfile`
- `.env.example`
- `db/init/001_schema.sql`
- `db/sqlite/001_schema.sql`
- `db/migrations/*.sql`
- `scripts/*.sh`
- `systemd/*.service`
- `systemd/*.timer`
- `deploy/rpi1/*`

## Common Pitfalls

- Assuming Supabase or PostgreSQL is the only persistence backend. SQLite is a
  supported backend too.
- Treating SQLite as a network service. It is a local database file and should
  be accessed through the repository/API boundary.
- Replacing an active SQLite file while the API is using it. Stop the target API
  before a final database replacement.
- Assuming production Compose exposes services publicly. It binds API, frontend,
  and pgAdmin to `127.0.0.1` by default.
- Assuming SEC EDGAR is the default live provider. It is not.
- Treating `VITE_API_AUTH_TOKEN` as private after it is built into frontend
  assets.
- Using ticker+metric as an alert identity when duplicate metric alerts exist.
- Claiming AI valuation has historical norms or sector comparisons. It only has
  the explicit backend data pack.
- Claiming frontend tests exist. They do not currently exist.
- Running destructive Docker commands such as `docker compose down -v` during
  normal troubleshooting.
