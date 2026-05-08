# FundamenTracker

FundamenTracker is a self-hosted fundamental investing tracker. It combines a
FastAPI backend, a React/Vite frontend, Docker Compose deployment, alert
scanning, optional Telegram notifications, and optional Gemini-based analysis.

This repository currently runs as a personal investment-monitoring app, not as a
general multi-user SaaS product. Some long-term architecture goals are already
started, but not every planned provider, database feature, or AI contract is
implemented yet.

## Current Features

- Watchlist storage with one or more alerts per ticker.
- Absolute alerts such as `PE < 20`.
- Relative alerts that compare current value to a captured reference value.
- ID-based alert update, delete, and toggle routes so duplicate ticker/metric
  alerts can be managed safely.
- Manual and periodic alert scanning.
- Signal Inbox for open investor-relevant events created from newly triggered
  alerts.
- Market metric and history lookup through `MarketDataService`.
- yfinance provider for quotes, metrics, symbol search, market overview, and
  historical chart data.
- Metric snapshot cache and provider-health rows through the repository layer.
- SEC EDGAR provider module for selected audited US fundamentals. It exists and
  has tests, but it is not the default provider selected by the live API.
- Optional Telegram notifications and command polling.
- Gemini valuation endpoint that returns a plain text analysis string.
- Local PostgreSQL and Supabase REST repository implementations.
- Development and production Docker Compose files.
- systemd units, watchdog script, migration runner, and PostgreSQL backup script.

## Known Limitations

- The Gemini endpoint is implemented as a service, but it currently returns
  `{"analysis": "..."}` text instead of a structured valuation object with
  explicit warnings and disclaimer fields.
- Tags and basic watchlist metadata are persisted in the backend database.
- The frontend has no committed Vitest test files and no `npm test` script.
- The default live provider is yfinance. Multi-provider arbitration and provider
  disagreement reporting are planned, not implemented.
- `api/main.py`, `api/supabase_db.py`, `api/state.py`, and `api/watchlist.py`
  are legacy Telegram/CLI-era modules. The active web API entrypoint is
  `api.api:app`.

## Documentation Map

- [Architecture](docs/ARCHITECTURE.md): active request, scanner, repository, and
  market-data flows.
- [Code Documentation](docs/CODE_DOCUMENTATION.md): practical map of active and
  legacy modules.
- [Host Setup](docs/HOST_SETUP.md): clone-to-Linux-host setup and operations.
- [Deployment Sequence](docs/DEPLOYMENT_SEQUENCE.md): dev/prod Compose usage and
  public exposure notes.
- [Local PostgreSQL](docs/LOCAL_DATABASE.md): PostgreSQL backend, migrations,
  pgAdmin, and Supabase compatibility.
- [SQL Tables](docs/SQL_TABLES.md): current schema and migration notes.
- [Data Sources](docs/DATA_SOURCES.md): yfinance, SEC EDGAR, metric cache, and
  provider-health behavior.
- [Security](docs/SECURITY.md) and
  [Security Hardening](docs/SECURITY_HARDENING.md): API token, CORS, frontend
  token limitations, and safe exposure modes.
- [Testing](docs/TESTING.md): current backend/CI test commands and test gaps.
- [Watchdog](docs/WATCHDOG.md): systemd watchdog behavior.
- [Frontend README](frontend/README.md): frontend-specific setup and structure.
- [ISSUES](ISSUES.md): historical scratchpad; active work is not tracked there.

## Requirements

The project is tested in CI with:

- Python 3.13 for backend tests.
- Node.js 22 for frontend builds.
- Docker Compose for compose-file validation.

The backend Docker image currently uses `python:3.11-slim`, and the frontend
Docker image uses `node:20-alpine`. Local development usually works with modern
Python 3.11+ and Node 20+, but CI is the authoritative validation target.

## Environment Variables

Copy the example file and fill in local values:

```bash
cp .env.example .env
```

Never commit real Supabase keys, Gemini keys, Telegram tokens, Cloudflare tunnel
tokens, API tokens, database passwords, or chat IDs.

Important variables:

- `API_AUTH_TOKEN`: bearer token required by mutable and sensitive read
  endpoints.
- `CORS_ALLOWED_ORIGINS`: comma-separated exact browser origins.
- `ALLOW_WILDCARD_CORS`: must be `true` as well as `CORS_ALLOWED_ORIGINS=*` to
  allow wildcard CORS.
- `DATABASE_BACKEND`: `postgres` or `supabase_rest`.
- `DATABASE_URL`: required by the API when `DATABASE_BACKEND=postgres`, unless
  production Compose derives it from the PostgreSQL variables.
- `SUPABASE_URL` and `SUPABASE_KEY`: required only for
  `DATABASE_BACKEND=supabase_rest`.
- `VITE_API_URL`: backend URL embedded into the frontend build.
- `VITE_API_AUTH_TOKEN`: optional frontend convenience token; it is visible to
  anyone who can load the frontend bundle.
- `GEMINI_API_KEY`: required only for `/ai-valuation`.
- `TELEGRAM_TOKEN` and `TELEGRAM_CHAT_ID`: required only for Telegram.
- `SEC_USER_AGENT`, `SEC_RATE_LIMIT_SECONDS`, `SEC_TICKER_CACHE_PATH`: SEC
  provider settings.

See `.env.example` for the full template.

## API Security

Protected endpoints expect:

```text
Authorization: Bearer <API_AUTH_TOKEN>
```

Public endpoints:

- `GET /health/live`
- `GET /server-time`
- `GET /search`
- `GET /market-overview`

`GET /health/ready` is protected unless `PUBLIC_READY_HEALTH=true`.
`GET /watchlist` is protected unless `READONLY_PUBLIC=true`.

`VITE_API_AUTH_TOKEN` is embedded into public Vite assets. It is acceptable for
trusted/private deployments, but it is not strong authentication for an
unprotected internet-facing frontend. Use Cloudflare Access, VPN, or future real
session authentication for public exposure.

## Common Commands

| Command | What it does |
| --- | --- |
| `make dev-up` | Build and start the development API and frontend. |
| `make dev-down` | Stop the development stack. |
| `make prod-up` | Build and start default production services (`postgres` and `api`). |
| `make prod-down` | Stop production containers without removing data. |
| `make logs` | Follow production logs. Use `LOG_SERVICES=api` to focus one service. |
| `make test` | Run backend tests with `pytest`. |
| `make frontend-build` | Run `npm run build` in `frontend/`. |
| `make health` | Check `HEALTH_URL`, defaulting to `/health/ready`. Reads `API_AUTH_TOKEN` from `.env` when present. |
| `make db-migrate` | Apply pending local PostgreSQL migrations. |
| `make backup-db` | Write a local PostgreSQL custom-format dump to `/srv/fundamentracker/backups` unless `BACKUP_DIR` is set. |
| `make install-systemd` | Install and start the production systemd units. |

Frontend lint exists as `cd frontend && npm run lint`, but CI does not enforce it
yet because it currently fails on existing React hooks and TypeScript lint
issues. There is no frontend `npm test` script at the moment.

Python commands such as `pytest` and `make test` assume the Python dependencies
are installed and the relevant virtual environment is active. In this checkout,
`.venv/bin/python -m pytest` is the direct non-activated form.

## Running Locally

Create `.env` first:

```bash
cp .env.example .env
```

Use the development compose file for local work. It keeps FastAPI reload, bind
mounts, and the Vite dev server.

```bash
docker compose -f docker-compose.dev.yml config
docker compose -f docker-compose.dev.yml up --build api frontend
```

Local URLs:

- Frontend UI: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- Live health: `http://localhost:8000/health/live`

If you use `DATABASE_BACKEND=postgres` in development, start the production
PostgreSQL service first or provide another reachable `DATABASE_URL`:

```bash
docker compose -f docker-compose.prod.yml up -d postgres
docker compose -f docker-compose.dev.yml up --build api frontend
```

`docker-compose.yml` is a backwards-compatible development alias. Prefer
`docker-compose.dev.yml` and `docker-compose.prod.yml` in new docs and commands.

## Supported Alert Metrics

The live yfinance metric catalog is defined in
`api/market_data/metric_definitions.py` and exposed to clients through public
`GET /metrics/catalog`. API calls reject unsupported metric keys instead of
falling back to price.

- `pe` (Trailing P/E)
- `fpe` (Forward P/E)
- `pb` (Price to Book)
- `evebitda` (EV/EBITDA)
- `roe` (Return on Equity)
- `roic` (Return on Invested Capital)
- `dividendyield` (Dividend Yield)
- `payoutratio` (Payout Ratio)
- `debttoequity` (Debt to Equity)
- `profitmargins` (Profit Margins)
- `operatingmargins` (Operating Margins)
- `price` (Current Price)

Supported operators are `<`, `>`, `<=`, `>=`, `==`, `=`, and `!=`.

## Alert Types

Absolute alerts compare the current metric directly to the configured target:

```text
PE < 20
```

Relative alerts compare current value to the reference value captured when the
alert is created:

```text
diff_percent = ((current_value / reference_value) - 1) * 100
```

The computed percentage difference is then compared with the configured target.
A target of `5` means `+5%`; a target of `-5` means `-5%`.

## Project Structure

- `api/api.py`: active FastAPI app, auth dependencies, startup tasks, and router
  registration.
- `api/routes/`: HTTP route modules.
- `api/services/`: application behavior split out from routes.
- `api/repositories/`: PostgreSQL and Supabase REST repository implementations.
- `api/db/migration_runner.py`: local PostgreSQL SQL migration runner.
- `api/market_data/`: market-data service, providers, normalizers, and metric
  definitions.
- `api/scanner.py`: alert evaluation loop used by manual and periodic scans.
- `api/telegram_service.py`: optional Telegram command polling and messages.
- `frontend/`: React/Vite/TypeScript frontend.
- `db/init/`: bootstrap schema for a new local PostgreSQL data directory.
- `db/migrations/`: explicit SQL migrations for existing local PostgreSQL
  databases.
- `scripts/`: systemd install/uninstall, watchdog, migration, backup, and API
  startup scripts.
- `systemd/`: production unit files.
- `tests/`: backend pytest suite with fakes and fixtures.
- `experimental/`: exploratory scripts that are not production entrypoints.

## Production Deployment

Production uses `docker-compose.prod.yml`. The default services are
`postgres` and `api`:

```bash
docker compose -f docker-compose.prod.yml config
docker compose -f docker-compose.prod.yml up -d --build
```

Production Compose sets:

- `APP_ENV=production`
- `DATABASE_BACKEND=postgres` when unset
- a Compose-network `DATABASE_URL` when unset
- API bind address `127.0.0.1:${API_PORT:-8000}`

Optional profiles:

```bash
# Static nginx-served frontend.
docker compose -f docker-compose.prod.yml --profile frontend up -d --build

# pgAdmin for local PostgreSQL administration.
docker compose -f docker-compose.prod.yml --profile dashboard up -d pgadmin

# Cloudflare Tunnel.
docker compose -f docker-compose.prod.yml --profile tunnel up -d
```

Set `DATABASE_BACKEND=supabase_rest`, `SUPABASE_URL`, and `SUPABASE_KEY` only
when the API should use Supabase REST instead of local PostgreSQL.

For a full host walkthrough, start with [Host Setup](docs/HOST_SETUP.md). For
the public-exposure sequence, see
[Deployment Sequence](docs/DEPLOYMENT_SEQUENCE.md).
