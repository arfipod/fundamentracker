# 📈 FundamenTracker

FundamenTracker is a powerful, full-stack stock fundamentals tracking application. It provides real-time alerts, historical data visualization, and AI-powered valuations to help you monitor the health of your investment portfolio.

- **Frontend:** React + Vite web interface with interactive Recharts.
- **Backend:** FastAPI service for watchlist operations, market scanning, and AI integrations.
- **Database:** Supabase PostgreSQL for reliable, relational state persistence.
- **Orchestration:** Docker Compose for consistent local deployments and Cloudflare Tunnels for easy remote access.

## Features

- **Live Watchlist & Alerts:** Track stocks and configure condition-based alerts (e.g., P/E < 20). Alerts transition gracefully to avoid spam.
- **Interactive Charting:** View historical data charts (up to 10+ years) for prices and fundamental metrics with ±1 Standard Deviation bands for quick historical context.
- **AI Valuations:** Get instant, AI-generated objective analyses on whether a stock is undervalued or overvalued using the Gemini API.
- **Tagging System:** Organize and filter your watchlist with custom tags.
- **Market Overview:** Get a quick glance at major indices (SPY, QQQ, DIA) directly from the dashboard.
- **Telegram Integration:** Manage alerts and receive notifications directly via Telegram.

## Environment Variables

Create a `.env` file in the repository root:

```env
# Database
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_or_service_key

# Optional: AI Valuation
GEMINI_API_KEY=your_google_gemini_api_key

# Optional: Telegram Notifications
TELEGRAM_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id

# Optional: Cloudflare Tunnel (for production remote access)
TUNNEL_TOKEN=your_cloudflare_tunnel_token
```

## Running Locally

To run the full stack locally, use Docker Compose:

```bash
sudo docker-compose up --build
```

After startup, access the application:
- **Frontend UI:** `http://localhost:5173`
- **Backend API:** `http://localhost:8000`

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
- `docker-compose.yml` — Orchestrates the API and frontend containers.

## Production Deployment

If your frontend is hosted on Vercel and your backend API runs on your local machine or Mini PC, the connection is automated via Cloudflare Tunnels using your `TUNNEL_TOKEN`.

For a full step-by-step guide on this setup, see **`docs/DEPLOYMENT_SEQUENCE.md`**.
