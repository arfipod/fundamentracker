# Deployment & Run Sequence

This guide explains the difference between the local development stack and the production Linux-host stack. Production can run only the API, the API plus a static frontend, the API plus Cloudflare Tunnel, or all three.

## Compose Files

- `docker-compose.dev.yml` is for local development. It keeps FastAPI `--reload`, bind mounts the repository into the API container, bind mounts `frontend/`, and runs the Vite dev server on port 5173.
- `docker-compose.prod.yml` is for production. It runs the API without `--reload`, does not bind mount source code, uses `restart: unless-stopped`, and health-checks `/health/live`.
- `docker-compose.yml` is kept as a backwards-compatible development alias. Prefer the explicit dev/prod files in new commands.

The service names remain `api`, `frontend`, and `cloudflared`.

---

## 1) Local Development

Create `.env` from the template:

```bash
cp .env.example .env
```

Validate and start the development stack:

```bash
docker compose -f docker-compose.dev.yml config
docker compose -f docker-compose.dev.yml up --build
```

Development URLs:

- Frontend UI: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- API live health: `http://localhost:8000/health/live`
- API readiness health: `http://localhost:8000/health/ready`

Health endpoints:

- `GET /health/live` confirms the FastAPI process is running. It does not check yfinance, Gemini, Telegram, or the database, so it is suitable for container liveness checks.
- `GET /health/ready` confirms required runtime configuration and minimum Supabase REST database connectivity. It returns HTTP 503 with non-sensitive failure details when the database is missing or unreachable.

---

## 2) One-time Production Setup

### 2.1 Install required tools
Make sure Docker and Docker Compose are installed. If you are using Ubuntu/Debian:

```bash
sudo apt update
sudo apt install -y ca-certificates curl gnupg lsb-release
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
$(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo usermod -aG docker $USER
```
*(Log out and back in after adding your user to the `docker` group).*

### 2.2 Create the `.env` file
The `.env` file is not tracked in git for security reasons. Create it from the example in the root folder of the repository on your Mini PC:

```bash
cp .env.example .env
```

Then edit `.env` and fill in your real values. Do not commit real secrets.

```env
SUPABASE_URL=https://example-project.supabase.co
SUPABASE_KEY=your_supabase_key
GEMINI_API_KEY=your_google_gemini_api_key
TELEGRAM_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
API_BIND_IP=127.0.0.1
API_PORT=8000
PROD_FRONTEND_PORT=8080
PUBLIC_API_URL=https://api.example.com
TUNNEL_TOKEN=your_cloudflare_tunnel_token
```

> **Note:** `TUNNEL_TOKEN` is required only when using the `tunnel` profile. Keep `API_BIND_IP=127.0.0.1` when Cloudflare Tunnel or a local reverse proxy is the only public entrypoint.

### 2.3 Configure Vercel (Hosted Frontend)
In your Vercel project dashboard (or via Vercel CLI), go to the **Environment Variables** settings and add:

- `VITE_API_URL` = your public API URL, for example `https://api.example.com`

You only need to do this once. As long as your domain stays the same, Vercel will always know how to reach your Mini PC.

---

## 3) Running Production

Validate the production compose file before starting it:

```bash
docker compose -f docker-compose.prod.yml config
```

### API only

Use this when Vercel hosts the frontend and another reverse proxy or tunnel exposes the API:

```bash
docker compose -f docker-compose.prod.yml up -d --build api
```

### API plus Cloudflare Tunnel

Use this when Cloudflare Tunnel should expose the local API:

```bash
docker compose -f docker-compose.prod.yml --profile tunnel up -d --build
```

What happens next:

1. Docker starts the FastAPI backend (`api`) on port 8000.
2. Docker waits for `/health/live` to pass.
3. Docker starts the `cloudflared` container.
4. `cloudflared` reads the tunnel configuration from `.env` and establishes a secure outbound connection to Cloudflare.

### API plus optional frontend

Use this when the Linux host should also serve the built React app through nginx:

```bash
docker compose -f docker-compose.prod.yml --profile frontend up -d --build
```

Set `PUBLIC_API_URL` in `.env` before building because Vite embeds it into the static frontend bundle.

---

## 4) Useful Commands

**View logs in real-time (to see API requests or tunnel status):**
```bash
docker compose -f docker-compose.prod.yml logs -f
```

**View logs only for the API:**
```bash
docker compose -f docker-compose.prod.yml logs -f api
```

**Check health status:**
```bash
docker compose -f docker-compose.prod.yml ps
curl http://127.0.0.1:8000/health/live
curl http://127.0.0.1:8000/health/ready
```

**Stop all services:**
```bash
docker compose -f docker-compose.prod.yml down
```

---

## 5) Troubleshooting

### Frontend shows "Failed to load resource" or "Network Error"
- Ensure the Mini PC is powered on and connected to the internet.
- Ensure the containers are running: `docker compose -f docker-compose.prod.yml ps`
- Check if the tunnel is healthy in the Cloudflare Zero Trust Dashboard -> Networks -> Tunnels.
- Make sure `VITE_API_URL` in Vercel or `PUBLIC_API_URL` in `.env` exactly matches your public API URL.

### API Container fails to boot
- Check that your `.env` file has the correct `SUPABASE_URL` and `SUPABASE_KEY`.
- View the logs: `docker compose -f docker-compose.prod.yml logs -f api` to see the Python error trace.
- Check the live endpoint locally: `curl http://127.0.0.1:8000/health/live`.
- Check database readiness locally: `curl http://127.0.0.1:8000/health/ready`. A 503 response means the API process is running but database configuration or connectivity needs attention.

### SSL Error (ERR_SSL_VERSION_OR_CIPHER_MISMATCH)
- This happens if you configure a sub-subdomain (like `api.fundamentracker.arfipod.org`) with Cloudflare's free Universal SSL. Use a single-level subdomain like `api-fundamentracker.arfipod.org` or `api.arfipod.org`.
