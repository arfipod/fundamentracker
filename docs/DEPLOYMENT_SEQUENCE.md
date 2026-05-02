# Deployment & Run Sequence (Vercel Frontend + Mini PC API + Cloudflare Tunnel)

This guide provides the exact steps to run your backend API on your Mini PC (or any local machine) and connect it securely to your Vercel frontend using a permanent Cloudflare Tunnel.

---

## 1) One-time setup (do this once on your Mini PC)

### 1.1 Install required tools
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

### 1.2 Create the `.env` file
The `.env` file is not tracked in git for security reasons. You must create it in the root folder of the repository on your Mini PC.

```env
SUPABASE_URL="your_supabase_url"
SUPABASE_KEY="your_supabase_anon_or_service_key"
TELEGRAM_TOKEN="your_telegram_bot_token"
TELEGRAM_CHAT_ID="your_telegram_chat_id"
TUNNEL_TOKEN="your_cloudflare_tunnel_token"
```

> **Note:** The `TUNNEL_TOKEN` allows your local machine to automatically link to `https://api-fundamentracker.arfipod.org` without needing to open ports on your router.

### 1.3 Configure Vercel (Frontend)
In your Vercel project dashboard (or via Vercel CLI), go to the **Environment Variables** settings and add:

- `VITE_API_URL` = `https://api-fundamentracker.arfipod.org`

You only need to do this once. As long as your domain stays the same, Vercel will always know how to reach your Mini PC.

---

## 2) Running the Backend (Daily/Routine)

Whenever you restart your Mini PC or want to bring the server up, simply navigate to the project folder and run:

```bash
docker compose up -d --build
```

**What happens next?**
1. Docker starts the FastAPI backend (`api`) on port 8000.
2. Docker starts the `cloudflared` container.
3. `cloudflared` reads the `TUNNEL_TOKEN` and establishes a secure outbound connection to Cloudflare.
4. Your API is instantly available at `https://api-fundamentracker.arfipod.org`.

There is no need to deploy or update Vercel again. The connection is permanent and automatic!

---

## 3) Useful Commands

**View logs in real-time (to see API requests or tunnel status):**
```bash
docker compose logs -f
```

**View logs only for the API:**
```bash
docker compose logs -f api
```

**Stop all services:**
```bash
docker compose down
```

---

## 4) Troubleshooting

### Frontend shows "Failed to load resource" or "Network Error"
- Ensure the Mini PC is powered on and connected to the internet.
- Ensure the containers are running: `docker compose ps`
- Check if the tunnel is healthy in the Cloudflare Zero Trust Dashboard -> Networks -> Tunnels.
- Make sure `VITE_API_URL` in Vercel exactly matches `https://api-fundamentracker.arfipod.org`.

### API Container fails to boot
- Check that your `.env` file has the correct `SUPABASE_URL` and `SUPABASE_KEY`.
- View the logs: `docker compose logs -f api` to see the Python error trace.

### SSL Error (ERR_SSL_VERSION_OR_CIPHER_MISMATCH)
- This happens if you configure a sub-subdomain (like `api.fundamentracker.arfipod.org`) with Cloudflare's free Universal SSL. Use a single-level subdomain like `api-fundamentracker.arfipod.org` or `api.arfipod.org`.
