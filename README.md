# 📈 FundamenTracker

FundamenTracker is a powerful, full-stack stock fundamentals tracking application. It provides real-time alerts, historical data visualization, and AI-powered valuations to help you monitor the health of your investment portfolio.

- **Frontend:** React + Vite web interface with interactive Recharts.
- **Backend:** FastAPI service for watchlist operations, market scanning, and AI integrations.
- **Database:** Supabase PostgreSQL for reliable, relational state persistence.
- **Orchestration:** Separate Docker Compose files for local development and Linux-host production, with optional Cloudflare Tunnel access.

## Features

- **Live Watchlist & Alerts:** Track stocks and configure condition-based alerts (e.g., P/E < 20). Alerts transition gracefully to avoid spam.
- **Interactive Charting:** View historical data charts (up to 10+ years) for prices and fundamental metrics with ±1 Standard Deviation bands for quick historical context.
- **AI Valuations:** Get instant, AI-generated objective analyses on whether a stock is undervalued or overvalued using the Gemini API.
- **Tagging System:** Organize and filter your watchlist with custom tags.
- **Market Overview:** Get a quick glance at major indices (SPY, QQQ, DIA) directly from the dashboard.
- **Telegram Integration:** Manage alerts and receive notifications directly via Telegram.

## Environment Variables

Copy the example file and fill in your own values:

```bash
cp .env.example .env
```

`.env.example` documents the development and production variables. Never commit real Supabase keys, Gemini keys, Telegram tokens, Cloudflare tunnel tokens, or chat IDs.

## Running Locally

Use the development compose file for local work. It keeps FastAPI reload, bind mounts, and the Vite dev server.

```bash
docker compose -f docker-compose.dev.yml config
docker compose -f docker-compose.dev.yml up --build
```

After startup, access the application:
- **Frontend UI:** `http://localhost:5173`
- **Backend API:** `http://localhost:8000`

`docker-compose.yml` is kept as a backwards-compatible development alias, but new commands should use `docker-compose.dev.yml` explicitly.

## Supported Metrics

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

## Supported Operators

- `<`, `>`, `<=`, `>=`, `==`, `=`, `!=`

## Project Structure

- `api/api.py` — FastAPI REST API handling watchlist, scan, and AI endpoints.
- `api/db/` — Database layer connecting to Supabase tables (`tickers`, `alerts`, `alert_history`, etc.).
- `api/telegram_service.py` — Telegram API polling and command parsing.
- `api/scanner.py` — Periodic evaluation of active alerts against live `yfinance` data.
- `frontend/` — React frontend containing modular components (`TickerCard`, `TickerRow`, `WatchlistSection`).
- `docker-compose.dev.yml` — Local development stack with reload, bind mounts, Vite dev server, and the existing `api`, `frontend`, and `cloudflared` service names.
- `docker-compose.prod.yml` — Production stack for Linux hosts. It removes reload and source bind mounts, adds API health checks, and makes `frontend` and `cloudflared` optional profiles.
- `docker-compose.yml` — Backwards-compatible development alias.

## Production Deployment

Production uses `docker-compose.prod.yml`. It runs the API without `--reload`, does not bind mount source code, uses `restart: unless-stopped`, and health-checks `/health/live`.

Validate and start the API:

```bash
docker compose -f docker-compose.prod.yml config
docker compose -f docker-compose.prod.yml up -d --build api
```

Optional production services:

```bash
# Include the static nginx-served frontend.
docker compose -f docker-compose.prod.yml --profile frontend up -d --build

# Include Cloudflare Tunnel.
docker compose -f docker-compose.prod.yml --profile tunnel up -d --build
```

If your frontend is hosted on Vercel and your backend API runs on your local machine or Mini PC, the connection can be automated via Cloudflare Tunnels using your `TUNNEL_TOKEN`.

For a full step-by-step guide on this setup, see **`docs/DEPLOYMENT_SEQUENCE.md`**.
