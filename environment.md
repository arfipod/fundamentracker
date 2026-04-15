# Environment Setup Guide

This guide explains how to run FundamenTracker with the **recommended Docker Compose workflow**, plus an optional local Python-only setup for development without Docker.

## 1) Recommended approach: Docker Compose

### Create `.env` in the repository root

Create a `.env` file at the root of the project with the following values:

```env
JSONBIN_ID=your_jsonbin_document_id
JSONBIN_KEY=your_jsonbin_master_key
TELEGRAM_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
```

- `JSONBIN_ID` and `JSONBIN_KEY` are required for persistence.
- `TELEGRAM_TOKEN` and `TELEGRAM_CHAT_ID` are required only if you want Telegram notifications.

### Build and run all services

```bash
docker-compose up --build
```

Services exposed by default:

- Backend API: `http://localhost:8000`
- Frontend UI: `http://localhost:5173`

### Stop services

```bash
docker-compose down
```

## 2) Optional: Local development without Docker

Use this only when you explicitly need to run backend code directly on your host environment.

### Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Install dependencies

```bash
pip install -r requirements.txt
```

### Provide environment variables

Use the same `.env` keys shown above, or export them directly in your shell.

### Run backend locally

```bash
python src/main.py
```

### Run tests

```bash
pytest
```

### Deactivate environment

```bash
deactivate
```

## Quick Git hygiene

- Do not commit `.venv/`.
- Keep `.env` private and never commit secrets.
- Update `requirements.txt` when Python dependencies change.


## 3) Production flow: Vercel frontend + mini PC API tunnel

When your backend runs on your mini PC and frontend is deployed on Vercel, use this order:

```bash
./start_tunnel.sh
vercel --prod
```

Why this order matters:
- `start_tunnel.sh` creates a fresh `trycloudflare.com` URL and updates Vercel `VITE_API_URL`.
- `vercel --prod` rebuilds the frontend so it uses the updated variable.

For the complete operational checklist, see `DEPLOYMENT_SEQUENCE.md`.
