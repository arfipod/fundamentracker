# 📈 FundamenTracker

FundamenTracker is a full-stack stock fundamentals tracking application.

- **Backend:** FastAPI service that exposes watchlist and scan operations.
- **Frontend:** React + Vite web interface that consumes the API.
- **Orchestration:** Docker Compose for consistent local and server deployments.
- **Core logic:** State persistence, alert transitions, supported metrics/operators, and Telegram alerting remain aligned with the original project behavior.

## What it does

- Manages a stock watchlist with configurable fundamental alerts.
- Fetches market fundamentals from Yahoo Finance (`yfinance`).
- Triggers alerts only on condition transitions (prevents duplicate spam while a condition remains true).
- Persists state in JSONBin.
- Sends optional Telegram notifications when scan conditions are met.

## Project structure

- `src/api.py` — FastAPI REST API (watchlist management and scan endpoints).
- `src/main.py` — legacy/secondary Python entrypoint for CLI and local testing.
- `src/config.py` — supported metric and operator mappings.
- `src/telegram_service.py` — Telegram API helpers and command parsing.
- `src/watchlist.py` — watchlist mutation utilities and metric parsing.
- `src/scanner.py` — scan and alert transition logic.
- `src/jsonbin.py` — state load/save integration with JSONBin.
- `src/state.py` — default state and state-shape guards.
- `frontend/` — React + Vite application.
- `docker-compose.yml` — multi-service orchestration for API + frontend.

## Environment variables

Create a `.env` file in the repository root:

```env
JSONBIN_ID=your_jsonbin_document_id
JSONBIN_KEY=your_jsonbin_master_key
TELEGRAM_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
```

> Telegram variables are optional if you only want API/UI functionality without Telegram notifications.

## Run with Docker Compose (recommended)

```bash
docker-compose up --build
```

After startup:

- API: `http://localhost:8000`
- Frontend: `http://localhost:5173`

## State schema

```json
{
  "watchlist": {
    "AAPL": {
      "name": "Apple Inc.",
      "alerts": [
        {
          "metric": "pe",
          "operator": "<",
          "target": 20.0,
          "is_triggered": false
        }
      ]
    }
  },
  "last_update_id": 0
}
```

## Supported metrics

- `pe` → `trailingPE`
- `fpe` → `forwardPE`
- `pb` → `priceToBook`
- `evebitda` → `enterpriseToEbitda`
- `roe` → `returnOnEquity`
- `price` → `currentPrice`

## Supported operators

- `<`, `>`, `<=`, `>=`, `==`, `=`, `!=`

## Telegram commands

- `/add TICKER VALUE` — Adds an alert using defaults: `pe < VALUE`.
- `/add TICKER METRIC OP VALUE` — Adds an alert with explicit metric/operator.
- `/remove TICKER` — Removes a ticker (and all alerts under it).
- `/list` — Lists watchlist entries and current metric values.
- `/alerts` — Lists alert configuration and current trigger status.
- `/state` — Shows the full raw state object.
- `/resetstate` — Clears the watchlist and resets update offset.
- `/help` — Shows available commands.
