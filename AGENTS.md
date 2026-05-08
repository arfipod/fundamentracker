# AGENTS.md — FundamenTracker

## Project Mission

FundamenTracker is a self-hosted fundamental investing tracker.

Its purpose is to help an individual investor monitor companies, valuation metrics, alerts, historical fundamentals, market data quality, and AI-assisted analysis in a reliable, transparent and auditable way.

The long-term goal is not to be a thin wrapper around `yfinance`, but a robust personal investment intelligence system with:

- FastAPI backend.
- React/Vite frontend.
- Docker-based deployment.
- Linux host/systemd operation.
- Optional local PostgreSQL database.
- Optional external data providers.
- Market data abstraction layer.
- Alert scanner.
- Telegram notifications.
- AI valuation with explicit data sources.
- Clear documentation for clone → configure → run → operate → recover.

Do not optimize only for quick hacks. Optimize for maintainability, reproducibility, reliability and clear ownership of data.

---

## Current Architecture

The current project is a full-stack application with:

- Backend: FastAPI.
- Frontend: React + Vite + TypeScript.
- Data source: currently mainly `yfinance`.
- Persistence: currently Supabase REST, with planned support for local PostgreSQL.
- Deployment: Docker Compose, Cloudflare Tunnel, Linux host.
- Notifications: Telegram Bot API.
- AI: Gemini-based valuation endpoint.

Important current entrypoints:

- Backend app: `api/api.py`, exposed as `api.api:app`.
- Frontend app: `frontend/src/App.tsx`.
- Current DB client: `api/db/client.py`.
- Scanner: `api/scanner.py`.
- Telegram integration: `api/telegram_service.py`.
- Docker Compose currently exists but may be split into dev/prod compose files.

Some legacy files may exist. Do not assume every file is active. Before deleting or refactoring suspicious files, inspect imports and runtime entrypoints.

---

## Strategic Direction

When making changes, favor this target architecture:

```text
frontend/
  React UI
  typed API client
  reusable components
  hooks

api/
  routes/
  schemas/
  services/
  repositories/
  market_data/
    providers/
      yfinance_provider.py
      sec_edgar_provider.py
      alpha_vantage_provider.py
      fmp_provider.py
    service.py
    normalizers.py
    metric_definitions.py
  core/
    settings.py
    security.py
    logging.py

db/
  init/
  migrations/

scripts/
  install-systemd.sh
  watchdog.sh
  backup-db.sh
  restore-db.sh

systemd/
  fundamentracker.service
  fundamentracker-watchdog.service
  fundamentracker-watchdog.timer

docs/
  HOST_SETUP.md
  LOCAL_DATABASE.md
  BACKUPS.md
  WATCHDOG.md
  DATA_SOURCES.md
  ARCHITECTURE.md
  TESTING.md
```

Do not perform massive architecture rewrites in one step. Prefer incremental, reviewable PRs.

---

## Core Principles

### 1. Preserve user data

Never delete, reset or recreate persisted user data unless explicitly requested.

Be especially careful with:

- PostgreSQL volumes.
- Supabase data.
- alert history.
- watchlist.
- tags.
- valuation history.
- provider snapshots.

Scripts must be conservative by default. Any destructive operation must require explicit confirmation.

### 2. No secrets in code

Never commit real API keys, tokens, chat IDs, database passwords or tunnel tokens.

Use `.env.example` with dummy values.

Secrets may include:

- `SUPABASE_KEY`
- `SUPABASE_URL`
- `DATABASE_URL`
- `POSTGRES_PASSWORD`
- `GEMINI_API_KEY`
- `TELEGRAM_TOKEN`
- `TELEGRAM_CHAT_ID`
- `TUNNEL_TOKEN`
- `API_AUTH_TOKEN`
- `ALPHAVANTAGE_API_KEY`
- `FMP_API_KEY`
- `SEC_USER_AGENT` if it contains personal contact info

### 3. Avoid direct external calls in tests

Tests must not call:

- Yahoo Finance.
- SEC EDGAR.
- Alpha Vantage.
- Financial Modeling Prep.
- Gemini.
- Telegram.
- Supabase production.
- Cloudflare.

Use fixtures, fakes, mocks or local test containers.

### 4. Prefer explicit contracts

Use typed schemas and response models where practical.

Backend contracts should be stable and documented.

Frontend should not infer hidden backend behavior.

### 5. Optimize for self-hosting

The project should be easy to run on a Linux host or Mini PC.

Prioritize:

- Docker Compose prod/dev separation.
- systemd autostart.
- watchdog.
- health endpoints.
- backup/restore scripts.
- local DB option.
- clear docs.

### 6. Make financial data auditable

Every market/fundamental value should ideally carry:

- source.
- fetched_at.
- as_of_date.
- confidence.
- stale flag if applicable.
- raw payload reference or snapshot when practical.

Do not hide disagreements between data providers. Surface them.

### 7. AI must be grounded

AI valuation must not invent data.

AI analysis should use an explicit input data pack and return structured output containing:

- verdict.
- confidence.
- key points.
- risks.
- data sources.
- warnings.
- disclaimer.

Always include a disclaimer that output is not financial advice.

---

## Coding Guidelines

### Python backend

Use readable, explicit Python.

Prefer:

- small functions.
- dependency injection for services.
- pure functions for calculations.
- typed Pydantic schemas.
- clear domain names.
- explicit exceptions.

Avoid:

- large route handlers with business logic.
- hidden global mutable state.
- direct `os.getenv` scattered everywhere.
- direct `yf.Ticker()` calls inside route handlers.
- direct `requests` calls without timeout.
- broad `except:` without logging/context.
- printing secrets or full tokens.

Target backend shape:

```text
route -> schema validation -> service -> repository/provider -> response schema
```

### FastAPI

Routes should be thin.

Good route handler:

```python
@router.post("/scan")
def scan_watchlist(
    scanner: AlertScannerService = Depends(get_scanner_service),
):
    result = scanner.run_once()
    return ScanResponse.from_result(result)
```

Bad route handler:

```python
@router.post("/scan")
def scan_watchlist():
    import yfinance as yf
    # fetch data, evaluate alerts, update DB, send telegram...
```

### Market data

Do not add new direct calls to `yfinance` from routes or UI-specific code.

Use `MarketDataService`.

Preferred flow:

```text
API route / scanner
  -> MarketDataService
  -> provider
  -> normalizer
  -> snapshots/cache
  -> response with source/confidence
```

Data providers should be optional and failure-tolerant.

A missing optional provider API key must not break the whole app.

### Database

The project may support two persistence modes:

- `supabase_rest`
- `postgres`

Do not hardcode one backend in business logic.

Use repositories or service abstractions.

If adding local PostgreSQL support, preserve existing Supabase behavior unless the task explicitly removes it.

### Frontend

Use TypeScript types.

Prefer:

- shared `apiClient`.
- reusable hooks.
- reusable components.
- metric catalog from backend.
- explicit loading/error/empty states.

Avoid:

- repeated `fetch(`${API_URL}...`)` across components.
- duplicated UI logic between `TickerRow` and `TickerCard`.
- storing domain data in `localStorage` unless it is only UI preference.
- hardcoded metric lists in many components.

Domain data such as tags should live in backend/DB. UI preferences may live in localStorage.

### Docker

Do not turn production compose into a development compose.

Production compose should generally:

- not use `--reload`.
- not mount the whole source tree.
- use `restart: unless-stopped`.
- define healthchecks.
- persist DB data in explicit host paths or named volumes.
- avoid exposing internal dashboards publicly by default.

Development compose may use:

- bind mounts.
- hot reload.
- Vite dev server.
- local ports.

### systemd and scripts

Shell scripts must use:

```bash
set -euo pipefail
```

Scripts must be idempotent where practical.

Do not hardcode a personal home directory.

Default production path may be:

```text
/opt/fundamentracker
```

Default data path may be:

```text
/srv/fundamentracker
```

Destructive scripts require confirmation.

### Documentation

Update docs when changing:

- environment variables.
- Docker commands.
- systemd units.
- DB schema.
- health endpoints.
- external providers.
- auth/security.
- backup/restore behavior.
- deployment flow.

Docs should include copy-pasteable commands.

---

## Testing Requirements

When changing backend behavior, add or update tests.

Minimum important test areas:

- health endpoints.
- auth.
- alert evaluation.
- absolute alerts.
- relative alerts.
- duplicate metric alerts.
- scanner transitions.
- market data normalization.
- provider failure handling.
- repository behavior.
- backup/watchdog scripts where practical.

Do not rely on internet in tests.

Prefer fake providers:

```python
class FakeMarketDataProvider:
    def get_metric(self, symbol: str, metric: str):
        ...
```

For frontend, prefer tests for:

- API client error handling.
- alert rendering.
- relative alert calculation.
- MetricChart stats.
- loading/error states.

---

## Quality Gates

Before finishing a code task, run the most relevant commands available.

Common backend checks:

```bash
pytest
```

Common frontend checks:

```bash
cd frontend
npm run build
npm run lint
npm test
```

Common Docker checks:

```bash
docker compose -f docker-compose.dev.yml config
docker compose -f docker-compose.prod.yml config
```

If a command cannot be run, explain why.

If a command fails due to unrelated pre-existing issues, clearly separate:

- what failed.
- why it failed.
- whether your changes caused it.
- recommended follow-up.

---

## Security Requirements

### API exposure

If the API is exposed through Cloudflare Tunnel or a public domain:

- Do not allow wildcard CORS by default.
- Protect mutable endpoints with `API_AUTH_TOKEN` or better auth.
- Keep `/health/live` public if needed.
- Consider whether `/health/ready` should expose DB readiness publicly.
- Never expose DB dashboards publicly by default.

### Dashboard exposure

pgAdmin/Adminer should bind to `127.0.0.1` by default.

If LAN access is needed, use an explicit env var such as:

```env
PGADMIN_BIND_IP=192.168.1.50
```

Do not expose DB dashboards through public tunnels unless behind strong auth.

### External restart endpoints

Do not implement public HTTP endpoints that restart Docker, systemd or host services.

Use local watchdog/systemd or secured SSH/VPN instead.

---

## Financial Data Rules

### Source priority

Initial recommended strategy:

```text
Price/current quote:
  1. yfinance
  2. optional paid/free market provider fallback

US audited fundamentals:
  1. SEC EDGAR
  2. FMP / Alpha Vantage fallback
  3. yfinance fallback

Forward estimates:
  1. yfinance or provider estimates
  2. mark clearly as estimates, not audited data

Calculated ratios:
  1. calculate internally from statements when possible
  2. compare with external provider ratios
  3. flag large disagreements
```

### Disagreements

Do not silently pick one value when providers disagree significantly.

Return or store:

- selected value.
- selected source.
- candidate values.
- confidence.
- warning.

### Stale data

If provider fails but cached data exists, returning stale data is acceptable only if marked clearly:

```json
{
  "value": 22.4,
  "source": "yfinance",
  "stale": true,
  "fetched_at": "..."
}
```

---

## Alert Rules

Alert operations should use `alert_id`, not only `ticker + metric`.

This is required because the user may create multiple alerts for the same ticker and metric.

Example:

```text
AAPL PE < 20
AAPL PE > 40
```

These must be separately editable and deletable.

### Relative alerts

Relative alerts compare current value to reference value:

```text
diff_percent = ((current_value / reference_value) - 1) * 100
```

Then evaluate:

```text
diff_percent operator target
```

Frontend and backend must use the same logic.

---

## AI Valuation Rules

AI valuation must be implemented as a service, not directly inside route handlers.

The service should:

1. Build a data pack.
2. Include sources and timestamps.
3. Include warnings about stale/missing/conflicting data.
4. Ask the model for structured JSON.
5. Return a disclaimer.
6. Avoid pretending certainty where data is weak.

Do not ask the model to “decide if a stock is a buy” without context and risk framing.

Preferred response shape:

```json
{
  "symbol": "AAPL",
  "verdict": "fair_value",
  "confidence": "medium",
  "key_points": [],
  "risks": [],
  "data_sources": [],
  "warnings": [],
  "disclaimer": "This is not financial advice."
}
```

---

## Task Execution Style

For each requested task:

1. Inspect the current files first.
2. Identify active vs legacy code.
3. Make the smallest coherent change.
4. Add tests.
5. Update docs.
6. Run relevant checks.
7. Summarize:
   - files changed.
   - behavior changed.
   - tests run.
   - risks.
   - follow-up tasks.

Do not bundle unrelated large refactors into one PR.

---

## Preferred PR Size

Good PR:

- one clear goal.
- tests included.
- docs included if needed.
- fewer than ~15 files changed unless it is an agreed architecture refactor.

Risky PR:

- changes backend, frontend, Docker, DB and docs all at once without a clear boundary.
- rewrites large files while changing behavior.
- removes files without proving they are unused.
- changes production deployment without docs.

---

## Suggested Work Order

Recommended high-impact order:

1. Health endpoints.
2. Split Docker dev/prod.
3. systemd service.
4. watchdog timer.
5. auth and CORS hardening.
6. alert CRUD by `alert_id`.
7. relative alert correctness.
8. backend tests.
9. MarketDataService.
10. YFinanceProvider behind MarketDataService.
11. SEC EDGAR provider.
12. metric snapshots and provider health.
13. local PostgreSQL support.
14. backup/restore.
15. frontend data-source visibility.
16. structured AI valuation.

---

## Files to Treat Carefully

Be careful with:

```text
api/api.py
api/db/client.py
api/scanner.py
api/telegram_service.py
frontend/src/hooks/useWatchlist.ts
frontend/src/components/AlertItem.tsx
frontend/src/components/TickerRow.tsx
frontend/src/components/TickerCard.tsx
docker-compose.yml
Dockerfile
frontend/Dockerfile
requirements.txt
.env.example
```

Before making large changes, inspect dependencies and usage.

---

## Legacy/Experimental Code

The repository may contain legacy or experimental files.

Do not assume these are production code.

Before modifying or deleting, check:

- imports.
- Docker entrypoints.
- README references.
- tests.
- docs.
- CLI usage.

Experimental scripts may be useful for ideas but should not contain absolute local paths or production assumptions.

---

## Final Response Format for Codex

Every completed task should end with:

```text
Summary:
- ...

Files changed:
- ...

Tests/checks run:
- ...

Known risks:
- ...

Recommended follow-ups:
- ...
```

If something could not be completed, be explicit and leave the repo in a safe state.
