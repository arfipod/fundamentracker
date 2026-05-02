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
- Persists state in Supabase.
- Sends optional Telegram notifications when scan conditions are met.

## Project structure

- `api/api.py` — FastAPI REST API (watchlist management and scan endpoints).
- `api/db/client.py` — REST client for managing relational state in Supabase.
- `api/config.py` — supported metric and operator mappings.
- `api/telegram_service.py` — Telegram API helpers and command parsing.
- `api/watchlist.py` — watchlist mutation utilities and metric parsing.
- `api/scanner.py` — scan and alert transition logic.
- `api/state.py` — legacy/removed components depending on Supabase implementation.
- `frontend/` — React + Vite application. [TODO Document all frontend components and their functionality]
- `docker-compose.yml` — multi-service orchestration for API + frontend.

## Environment variables

Create a `.env` file in the repository root:

```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_or_service_key
TELEGRAM_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
TUNNEL_TOKEN=your_cloudflare_tunnel_token
```

> Telegram variables are optional if you only want API/UI functionality without Telegram notifications.

## Install Docker on Ubuntu

If you are running Ubuntu, install Docker and Docker Compose with:

```bash
sudo apt update
sudo apt install -y ca-certificates curl gnupg lsb-release
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo usermod -aG docker $USER

# And after this, to use docker-compose

sudo ln -s /usr/libexec/docker/cli-plugins/docker-compose /usr/local/bin/docker-compose

# An to install vercel

npm install -g vercel
```

Then log out and back in for Docker group permissions to take effect.

## Run with Docker Compose (recommended)

```bash
sudo docker-compose up --build
```

After startup:

- API: `http://localhost:8000`
- Frontend: `http://localhost:5173`


## Vercel + Mini PC + Cloudflare Tunnel (production flow)

If your frontend is hosted on Vercel and your backend API runs on your local machine or mini PC, the architecture is fully automated via Cloudflare Tunnels using a permanent `TUNNEL_TOKEN`.

For a full step-by-step guide (initial setup, environment variables, running the server, and troubleshooting), see **`DEPLOYMENT_SEQUENCE.md`**.

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
- `roe` → `returnOnEquity` [BUG: This metric does not seem to be working correctly as all the shown ROE values are a single constant. Check if the logic is correct]
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
