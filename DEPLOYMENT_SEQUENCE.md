# Deployment & Run Sequence (Vercel Frontend + Mini PC API + Cloudflare Tunnel)

This guide is the **exact order of operations** to run your deployed Vercel frontend against the API running on your mini PC through Cloudflare Tunnel.

---

## 1) One-time setup (do this once)

### 1.1 Install required tools on the mini PC

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

Log out and back in after adding your user to the `docker` group.

Install Vercel CLI:

```bash
npm install -g vercel
```

### 1.2 Connect Vercel CLI to your account/project

Run in the repo root:

```bash
vercel login
vercel link
```

### 1.3 Create the backend `.env` file

Create `.env` at the repository root:

```env
JSONBIN_ID=your_jsonbin_document_id
JSONBIN_KEY=your_jsonbin_master_key
TELEGRAM_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
```

`JSONBIN_ID` and `JSONBIN_KEY` are required for persistence.

---

## 2) Daily run sequence (recommended)

Use this exact order whenever the mini PC restarts or containers are down.

### Step A — Start API + Cloudflare Tunnel and update Vercel env

```bash
./start_tunnel.sh
```

What this does automatically:
1. Starts `api` + `cloudflared` with Docker Compose.
2. Reads the generated `https://<random>.trycloudflare.com` URL.
3. Updates Vercel `VITE_API_URL` (production env var) with that URL.

### Step B — Trigger a production deploy on Vercel

```bash
vercel --prod
```

This is required because changing Vercel env vars does **not** update an already-built frontend.

### Step C — Validate end-to-end

1. Get your Vercel production URL (from CLI output).
2. Open the app and verify watchlist load/add/remove/scan.
3. Optional API check from terminal:

```bash
curl -sS "$VITE_API_URL/watchlist"
```

---

## 3) Correct restart order after a reboot

If mini PC or Docker restarts:

1. `./start_tunnel.sh`
2. `vercel --prod`
3. Open Vercel app and verify API connectivity.

If you skip step 2, frontend may still point to the old tunnel URL and fail.

---

## 4) Normal operations and useful commands

Start only backend + tunnel:

```bash
docker-compose up -d api cloudflared
```

View logs:

```bash
docker-compose logs -f api
docker-compose logs -f cloudflared
```

Stop all services:

```bash
docker-compose down
```

---

## 5) Troubleshooting checklist

### Problem: Vercel frontend shows network/CORS/API errors

Check:
1. Tunnel URL currently alive:
   ```bash
   docker-compose logs cloudflared | grep -Eo 'https://[a-zA-Z0-9-]+\.trycloudflare\.com' | head -n 1
   ```
2. Vercel env var set to same URL:
   ```bash
   vercel env pull .vercel.env
   rg 'VITE_API_URL' .vercel.env
   ```
3. Re-deploy after env change:
   ```bash
   vercel --prod
   ```

### Problem: `./start_tunnel.sh` cannot update env var

- Verify Vercel CLI auth: `vercel whoami`
- Ensure project is linked: `vercel link`

### Problem: API container fails to boot

- Ensure `.env` exists and has valid JSONBin credentials.
- Check logs: `docker-compose logs -f api`

---

## 6) Important behavior of `trycloudflare.com`

The current setup uses **ephemeral quick tunnels** (`*.trycloudflare.com`).
The URL usually changes when tunnel restarts.

That is why the safe sequence is always:
1. Start tunnel (`./start_tunnel.sh`)
2. Update Vercel env (script does this)
3. Re-deploy (`vercel --prod`)

---

## 7) Optional improvement for stability

If you want to avoid frequent redeploys, switch from quick tunnels to a **named Cloudflare Tunnel** with a stable hostname (for example `api.yourdomain.com`).
Then set `VITE_API_URL` once and keep it fixed.
