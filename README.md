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
- `frontend/` — React + Vite application.
- `docker-compose.yml` — multi-service orchestration for API + frontend.

## Environment variables

Create a `.env` file in the repository root:

```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_or_service_key
TELEGRAM_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
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

If your frontend is hosted on Vercel and your backend API runs on your mini PC, follow this sequence:

1. `./start_tunnel.sh` (starts API + tunnel and updates Vercel `VITE_API_URL`)
2. `vercel --prod` (rebuild frontend with the new env var)
3. Open your Vercel URL and verify API connectivity

For a full step-by-step guide (initial setup, reboot flow, troubleshooting), see **`DEPLOYMENT_SEQUENCE.md`**.

## Using `start_tunnel.sh`

If you need a temporary public tunnel for the local API and want to update the frontend deployment automatically, use `start_tunnel.sh`.

This script:

- starts the `api` and `cloudflared` containers in the background
- waits for Cloudflare Tunnel to generate a public `trycloudflare.com` URL
- updates the `VITE_API_URL` environment variable in Vercel

Run it with:

```bash
./start_tunnel.sh
```

Use this when you want to expose your local API publicly during development or testing, especially if your frontend is deployed on Vercel and needs to call the local backend.

> Note: `start_tunnel.sh` requires the `vercel` CLI to be installed and authenticated, and assumes your Vercel project uses `VITE_API_URL` for the API base URL.

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
