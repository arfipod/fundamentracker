# Testing

FundamenTracker backend tests use `pytest` and are configured by `pytest.ini`.
CI runs backend tests with Python 3.13.

## Run Backend Tests

From the repository root:

```bash
pytest
```

With a local virtual environment:

```bash
source .venv/bin/activate
python -m pytest
```

`pytest.ini` sets:

```ini
[pytest]
pythonpath = api
testpaths = tests
```

Tests can therefore import backend modules directly, and collection is limited
to `tests/`.

## Test Layout

Core coverage is split by module:

- `tests/test_health.py`: live and readiness health endpoints.
- `tests/test_alert_evaluation.py`: absolute and relative alert logic, invalid
  inputs, and duplicate same-metric rules.
- `tests/test_scanner.py`: scan transitions, inactive or missing metrics,
  relative alerts, duplicate IDs, history, and signals.
- `tests/test_alert_id_operations.py`: update, soft-delete, restore, and
  ambiguity behavior.
- `tests/test_repositories_fake.py`: fake repository behavior and watchlist
  shaping.
- `tests/test_market_data_normalizers.py`: symbol/value normalization plus
  point-in-time quarterly ROE, ROIC, margin, and debt/equity reconstruction.
- `tests/test_derived_metrics.py`: TTM valuation and cash metrics, owner earnings,
  reinvestment, leverage, growth, capital allocation, valuation context, and EPS
  revisions.
- `tests/test_market_data_service.py`: snapshot cache, provider health, yfinance
  provider behavior, real valuation-table history, API endpoints, and catalog.

Additional focused tests cover auth, CORS, database configuration, migrations,
operations status, Gemini valuation, and SEC EDGAR using local fixtures.

`tests/test_all.py` is a legacy placeholder; active coverage lives in focused
modules.

## No External Calls

Tests must not call real external services:

- Yahoo Finance / yfinance.
- SEC EDGAR.
- Gemini.
- Telegram.
- Supabase production.
- Cloudflare.

Use fakes, fixtures, monkeypatching, or local test containers. yfinance tests
must use fake `Ticker` objects and deterministic pandas DataFrames. In
particular, valuation-history tests must supply a fake
`get_valuation_measures()` table rather than depending on Yahoo availability.

## Useful Commands

Run all backend tests:

```bash
python -m pytest
```

Run market-data tests:

```bash
python -m pytest \
  tests/test_market_data_normalizers.py \
  tests/test_derived_metrics.py \
  tests/test_market_data_service.py
```

Run a single test:

```bash
python -m pytest tests/test_derived_metrics.py::test_core_valuation_and_cash_metrics
```

Show extra skip and failure context:

```bash
python -m pytest -ra
```

Run frontend build validation:

```bash
cd frontend
npm ci
npm run build
```

Run compose validation:

```bash
docker compose -f docker-compose.dev.yml config
docker compose -f docker-compose.prod.yml config
```

## Current Known Warnings And Gaps

The suite currently emits FastAPI deprecation warnings for `@app.on_event`.
These warnings do not fail tests, but should be addressed when startup moves to
lifespan handlers.

Frontend lint exists but is not enforced in CI because existing React hooks and
TypeScript lint issues are not yet clean. There is no frontend unit-test script;
CI validates the production TypeScript/Vite build.
