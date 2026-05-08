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

Configure API CORS with `CORS_ALLOWED_ORIGINS`, a comma-separated list of exact browser origins:

```env
CORS_ALLOWED_ORIGINS=http://localhost:5173,https://your-frontend.example.com
ALLOW_WILDCARD_CORS=false
```

The development compose stack sets `APP_ENV=development` and allows `http://localhost:5173` by default when no origins are configured. The production compose stack sets `APP_ENV=production`; production does not allow wildcard CORS unless `CORS_ALLOWED_ORIGINS=*` and `ALLOW_WILDCARD_CORS=true` are both set intentionally. If you run the API without Compose in production, set `APP_ENV=production` yourself.

## Common Commands

| Command | What it does |
| --- | --- |
| `make dev-up` | Builds and starts the development API and frontend with `docker-compose.dev.yml`. |
| `make dev-down` | Stops the development compose stack. |
| `make prod-up` | Builds and starts the default production services with `docker-compose.prod.yml`. |
| `make prod-down` | Stops the production compose stack without removing persisted data. |
| `make logs` | Follows production compose logs. Use `LOG_SERVICES=api` to focus one service. |
| `make test` | Runs backend tests with `pytest`. |
| `make frontend-build` | Builds the React/Vite frontend. |
| `make health` | Checks the API readiness endpoint. Override with `HEALTH_URL=...` if needed. |
| `make backup-db` | Writes a local PostgreSQL custom-format dump to `/srv/fundamentracker/backups`. Override with `BACKUP_DIR=...` if needed. |
| `make install-systemd` | Runs `sudo ./scripts/install-systemd.sh` to install and start the systemd units. |

## Running Locally

Use the development compose file for local work. It keeps FastAPI reload, bind mounts, and the Vite dev server.

```bash
docker compose -f docker-compose.dev.yml config
docker compose -f docker-compose.dev.yml up --build api frontend
```

After startup, access the application:
- **Frontend UI:** `http://localhost:5173`
- **Backend API:** `http://localhost:8000`

`docker-compose.yml` is kept as a backwards-compatible development alias, but new commands should use `docker-compose.dev.yml` explicitly.

For a complete clone-to-running-host walkthrough, including Docker installation, `/opt/fundamentracker` setup, `.env` configuration, dev/prod startup, systemd, health checks, pgAdmin, logs, backups, and troubleshooting, see **[`docs/HOST_SETUP.md`](docs/HOST_SETUP.md)**.

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

## Alert Types

- **Absolute value:** compares the current metric directly to the configured target, for example `PE < 20`.
- **Change (%):** compares the current metric to the reference value captured when the alert is created:

```text
diff_percent = ((current_value / reference_value) - 1) * 100
```

For relative alerts, the target is a percentage. A target of `5` means `+5%`; a target of `-5` means `-5%`. Relative alerts can be created from both the main Add Alert form and inline ticker controls.

## Project Structure

- `api/api.py` — FastAPI REST API handling watchlist, scan, and AI endpoints.
- `api/db/` — Database layer connecting to PostgreSQL or Supabase REST tables (`tickers`, `alerts`, `alert_history`, etc.).
- `api/telegram_service.py` — Telegram API polling and command parsing.
- `api/scanner.py` — Periodic evaluation of active alerts against live `yfinance` data.
- `frontend/` — React frontend containing modular components (`TickerCard`, `TickerRow`, `WatchlistSection`).
- `docker-compose.dev.yml` — Local development stack with reload, bind mounts, Vite dev server, and the existing `api`, `frontend`, and `cloudflared` service names.
- `docker-compose.prod.yml` — Production stack for Linux hosts. It removes reload and source bind mounts, adds API health checks, and makes `frontend` and `cloudflared` optional profiles.
- `docker-compose.yml` — Backwards-compatible development alias.

## Production Deployment

Production uses `docker-compose.prod.yml`. It runs the API without `--reload`, does not bind mount source code, uses `restart: unless-stopped`, and health-checks `/health/live`. The default production persistence mode is local PostgreSQL: `DATABASE_BACKEND` defaults to `postgres`, and `DATABASE_URL` defaults to the Compose `postgres` service.

Validate and start the default production services (`postgres` and `api`):

```bash
docker compose -f docker-compose.prod.yml config
docker compose -f docker-compose.prod.yml up -d --build
```

To keep using Supabase REST instead, set these values explicitly in `.env` before starting the API:

```env
DATABASE_BACKEND=supabase_rest
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-service-or-rest-key
```

Optional production services:

```bash
# Include the static nginx-served frontend.
docker compose -f docker-compose.prod.yml --profile frontend up -d --build

# Include Cloudflare Tunnel.
docker compose -f docker-compose.prod.yml --profile tunnel up -d --build
```

If your frontend is hosted on Vercel and your backend API runs on your local machine or Mini PC, the connection can be automated via Cloudflare Tunnels using your `TUNNEL_TOKEN`.

For a full host installation and operations guide, start with **[`docs/HOST_SETUP.md`](docs/HOST_SETUP.md)**. For the Cloudflare/Vercel-oriented deployment sequence, see **[`docs/DEPLOYMENT_SEQUENCE.md`](docs/DEPLOYMENT_SEQUENCE.md)**.
