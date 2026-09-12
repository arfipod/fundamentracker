# FundamenTracker

FundamenTracker is a self-hosted fundamental-investing tracker with a FastAPI
backend, React/Vite frontend, PostgreSQL, SQLite, or Supabase persistence,
scheduled alert scans, a Signal Inbox, optional Telegram notifications, and
optional structured Gemini analysis.

It is currently designed as a personal investment-monitoring application rather
than a general multi-user SaaS product.

## Current Features

- Watchlists with multiple absolute or relative alerts per ticker.
- ID-based alert update, toggle, soft-delete, restore, and history.
- Manual and periodic scans with newly triggered alerts copied to Signal Inbox.
- Current market metrics and historical charts through `MarketDataService`.
- `yfinance==1.5.2` for lightweight quotes, real Yahoo valuation history,
  statement-derived TTM metrics, growth, dilution, capital allocation, and
  analyst-revision signals.
- SEC EDGAR endpoint for selected audited US issuer facts.
- Persistent metric snapshots, stale-data fallback, and provider-health rows.
- React Explorer that clearly distinguishes historical metrics from metrics that
  only have a reliable current value.
- Structured Gemini valuation output with observations, risks, missing data,
  sources, disclaimer, and read-only alert ideas.
- Docker Compose, systemd units, migration runner, watchdog, and database backup
  scripts.

## Persistence Backends

FundamenTracker supports three repository backends through the same application
boundary:

- `postgres`: local or remote PostgreSQL, used by the production Compose stack.
- `sqlite`: lightweight file-backed persistence for single-host deployments.
- `supabase_rest`: Supabase persistence through its REST API.

For SQLite, configure:

```env
DATABASE_BACKEND=sqlite
SQLITE_PATH=/srv/fundamentracker/fundamentracker.db
```

The SQLite repository initializes the idempotent schema in
`db/sqlite/001_schema.sql`, enables foreign keys, uses WAL journal mode, and
sets a bounded busy timeout. PostgreSQL and Supabase behavior remain available
unchanged.

## Fundamental Metric Coverage

The authoritative catalog lives in
`api/market_data/metric_definitions.py` and is exposed through:

```text
GET /metrics/catalog
```

The catalog covers:

- Price and size: price, market capitalization, enterprise value.
- Valuation: trailing/forward/normalized P/E, PEG, P/S, P/B, EV/revenue,
  EV/EBITDA, EV/EBIT, P/FCF, earnings and FCF yields, owner-earnings yield after
  SBC, and five-year valuation median/percentile context.
- Profitability and quality: ROE, ROIC, gross/net/operating/FCF margins, cash
  conversion, interest coverage, and normalized-versus-GAAP EPS gap.
- Reinvestment and dilution: capex, SBC, R&D intensity, and diluted-share
  growth.
- Leverage and liquidity: debt/equity, net debt/EBITDA, net cash/market cap,
  current ratio, and quick ratio.
- Growth and revisions: revenue, operating-income, EPS, CFO, and FCF growth;
  margin changes; EPS estimate revisions.
- Shareholder return: dividend and payout ratios, buyback yields, and total
  shareholder yield.

Each catalog row states its unit, source kind, period, formula, alert support,
and history support. Percentage alert targets use display units: for example,
`fcf_yield_ttm > 5` means a yield above 5%, not 0.05.

## Reliable History Policy

FundamenTracker no longer constructs historical P/E, forward P/E, P/B, or
EV/EBITDA by combining old prices with current fundamentals. It now uses
`Ticker.get_valuation_measures(...)`, which supplies dated Yahoo valuation
observations.

Statement-derived histories such as ROE and ROIC use rolling quarterly flows and
point-in-time balance sheets. Most TTM, growth, allocation, and analyst metrics
are current-only until a defensible historical series exists; the frontend does
not fabricate a chart for them.

## Known Limitations

- yfinance is a best-effort, unofficial Yahoo Finance client. Values may be
  missing, delayed, restated, or unsuitable for a particular sector.
- Historical Yahoo valuation observations can be sparse.
- Normalized earnings use Yahoo's mapping and should be reviewed alongside GAAP
  values and unusual items.
- Banks, insurers, REITs, commodity businesses, and early-stage companies may
  require sector-specific ratios.
- Multi-provider arbitration and automatic disagreement reporting are not yet
  implemented.
- The frontend has no committed unit-test suite; CI validates its production
  TypeScript/Vite build.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Code map](docs/CODE_DOCUMENTATION.md)
- [Data sources](docs/DATA_SOURCES.md)
- [yfinance sources, formulas, and limitations](docs/yfinance_capabilities.md)
- [Testing](docs/TESTING.md)
- [Host setup](docs/HOST_SETUP.md)
- [Deployment sequence](docs/DEPLOYMENT_SEQUENCE.md)
- [Local PostgreSQL](docs/LOCAL_DATABASE.md)
- [SQL schema](docs/SQL_TABLES.md)
- [Security](docs/SECURITY.md)
- [Security hardening](docs/SECURITY_HARDENING.md)
- [Watchdog](docs/WATCHDOG.md)

## Supported Runtime

CI is authoritative and currently validates:

- Python 3.13 backend tests.
- Node.js 22 frontend build.
- Development and production Docker Compose configuration.

The backend image uses Python 3.11 and the frontend image uses Node 20.

## Local Development

Create local configuration from the example file, then start the development
stack:

```bash
cp .env.example .env
docker compose -f docker-compose.dev.yml up --build api frontend
```

Default local endpoints:

- Frontend: `http://localhost:5173`
- API: `http://localhost:8000`
- Live health: `http://localhost:8000/health/live`

For a PostgreSQL-backed development session, start the database service first or
provide another reachable database URL:

```bash
docker compose -f docker-compose.prod.yml up -d postgres
docker compose -f docker-compose.dev.yml up --build api frontend
```

For a lightweight local SQLite session, run the API natively with
`DATABASE_BACKEND=sqlite` and a writable `SQLITE_PATH`.

## Common Commands

| Command | Purpose |
| --- | --- |
| `make dev-up` | Build and start development API and frontend. |
| `make dev-down` | Stop the development stack. |
| `make prod-up` | Build and start production PostgreSQL and API. |
| `make prod-down` | Stop production services without deleting data. |
| `make test` | Run backend pytest suite. |
| `make frontend-build` | Build the frontend. |
| `make db-migrate` | Apply local PostgreSQL migrations. |
| `make backup-db` | Create a PostgreSQL backup. |
| `make health` | Check API readiness. |
| `make logs` | Follow service logs. |

Direct validation commands:

```bash
pytest
cd frontend && npm ci && npm run build
docker compose -f docker-compose.dev.yml config
docker compose -f docker-compose.prod.yml config
```

## Alert Semantics

Absolute alerts compare the current normalized display value with a target:

```text
pe < 16
fcf_yield_ttm > 5
roic > 20
```

Relative alerts compare the percentage change from the reference value captured
when the alert is created:

```text
diff_percent = ((current_value / reference_value) - 1) * 100
```

Supported operators are `<`, `>`, `<=`, `>=`, `==`, `=`, and `!=`.

## Project Structure

```text
api/api.py                              active FastAPI entrypoint
api/market_data/service.py              cache and provider boundary
api/market_data/providers/              live provider implementations
api/market_data/derived_metrics.py      deterministic fundamental formulas
api/market_data/metric_definitions.py   public metric catalog
api/scanner.py                          alert evaluation and signals
api/repositories/                       PostgreSQL, SQLite, Supabase repositories
frontend/                               React/Vite frontend
tests/                                  offline backend test suite
db/                                     PostgreSQL and SQLite schemas/migrations
scripts/ and systemd/                    host operations
```

Production deployment details, network exposure, authentication configuration,
and database operations are documented in the linked deployment and security
guides.
