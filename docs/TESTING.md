# Testing

FundamenTracker backend tests are written with `pytest` and are configured by
`pytest.ini`.

## Run Backend Tests

From the repository root:

```bash
source venv/bin/activate
pytest
```

If the virtual environment is not activated, use:

```bash
venv/bin/python -m pytest
```

`pytest.ini` sets:

```ini
[pytest]
pythonpath = api
testpaths = tests
```

That means tests can import backend modules directly, and collection is limited
to the `tests/` directory.

## Test Layout

Core backend coverage is split by module:

- `tests/test_health.py`: live and readiness health endpoints.
- `tests/test_alert_evaluation.py`: absolute alerts, relative alert percent
  differences, invalid inputs, and duplicate same-metric alert rules.
- `tests/test_scanner.py`: scanner behavior with fake market data and fake DB
  operations, including false-to-true transitions, already-triggered alerts,
  clearing triggered state, relative alerts, inactive alerts, missing data, and
  duplicate same-metric alerts by `alert_id`.
- `tests/test_alert_id_operations.py`: alert update/delete behavior for
  duplicate same-metric alerts, including deprecated ticker+metric route
  compatibility returning `409` instead of mutating ambiguous alerts.
- `tests/test_repositories_fake.py`: fake repository behavior and watchlist
  shaping without Supabase or PostgreSQL.
- `tests/test_market_data_normalizers.py`: symbol, numeric, metric, history,
  and historical fundamental normalizers.

Additional focused tests cover API auth, CORS, DB client configuration, market
data service caching/fallback behavior, and the SEC EDGAR provider using local
fixtures and fake request clients.

## No External Calls

Tests must not call real external services:

- Yahoo Finance / `yfinance`.
- SEC EDGAR.
- Gemini.
- Telegram.
- Supabase production.
- Cloudflare.

Use fakes, fixtures, monkeypatching, or local test containers. Provider tests
must inject fake request clients or monkeypatch provider dependencies so that
they remain deterministic and offline.

## Useful Commands

Run a specific module:

```bash
venv/bin/python -m pytest tests/test_scanner.py
```

Run one test by name:

```bash
venv/bin/python -m pytest tests/test_alert_evaluation.py::test_relative_alert_evaluation_compares_percent_diff_to_target
```

Show extra skip and failure context:

```bash
venv/bin/python -m pytest -ra
```

## Current Known Warning

The suite currently emits FastAPI deprecation warnings for `@app.on_event`.
These warnings do not fail tests, but should be addressed when the API startup
flow is moved to lifespan handlers.
