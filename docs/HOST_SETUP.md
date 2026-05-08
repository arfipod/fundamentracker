# Host Setup

This guide installs and operates FundamenTracker on a Linux host using Docker Compose. It is written for a self-hosted machine such as a Mini PC, VPS, or home server.

The production systemd units expect the repository to live at:

```text
/opt/fundamentracker
```

The default local data path for PostgreSQL is:

```text
/srv/fundamentracker
```

## 1. Linux Requirements

Use a current Linux distribution with systemd and Docker Engine support. Ubuntu LTS and Debian stable are the easiest paths.

Minimum practical host:

```text
CPU: 2 cores
RAM: 2 GB minimum, 4 GB recommended
Disk: 10 GB minimum, more if keeping PostgreSQL backups locally
Network: outbound HTTPS access for market data, Supabase, Gemini, Telegram, and Cloudflare Tunnel if enabled
```

Install baseline packages:

```bash
sudo apt update
sudo apt install -y ca-certificates curl git jq rsync
```

If your distribution does not use `apt`, install equivalent packages with your package manager and follow Docker's official instructions for your platform:

```text
https://docs.docker.com/engine/install/
```

## 2. Install Docker

These commands follow Docker's official apt repository flow for Ubuntu or Debian. Run them on the host.

Remove old conflicting Docker packages if they exist:

```bash
for pkg in docker.io docker-doc docker-compose docker-compose-v2 podman-docker containerd runc; do
  sudo apt remove -y "$pkg" || true
done
```

Add Docker's repository:

```bash
. /etc/os-release
sudo apt update
sudo apt install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL "https://download.docker.com/linux/${ID}/gpg" -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/${ID} ${VERSION_CODENAME} stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
```

Install Docker Engine and the Compose plugin:

```bash
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

Enable Docker at boot:

```bash
sudo systemctl enable --now docker
```

Verify the install:

```bash
sudo docker run --rm hello-world
sudo docker compose version
```

Optional: allow your current user to run Docker without `sudo`.

```bash
sudo usermod -aG docker "$USER"
newgrp docker
docker ps
```

If `docker ps` still says permission denied, log out and back in.

All later `docker compose ...` commands can be prefixed with `sudo` if you choose not to add your user to the Docker group.

## 3. Clone to /opt/fundamentracker

Clone the repository into the production path. Use your fork URL if you maintain one.

```bash
sudo mkdir -p /opt
sudo git clone https://github.com/arfipod/fundamentracker.git /opt/fundamentracker
sudo chown -R "$USER:$USER" /opt/fundamentracker
cd /opt/fundamentracker
```

If you already cloned elsewhere, copy it into place instead:

```bash
sudo mkdir -p /opt/fundamentracker
sudo rsync -a --delete ./ /opt/fundamentracker/
sudo chown -R "$USER:$USER" /opt/fundamentracker
cd /opt/fundamentracker
```

Check that the important files exist:

```bash
test -f docker-compose.dev.yml
test -f docker-compose.prod.yml
test -f .env.example
test -x scripts/install-systemd.sh
```

## 4. Create .env

Create a local environment file from the template:

```bash
cd /opt/fundamentracker
cp .env.example .env
chmod 600 .env
```

Edit it:

```bash
nano .env
```

At minimum, change these values:

```env
LOG_LEVEL=INFO
API_AUTH_TOKEN=replace-with-a-long-random-token
VITE_API_AUTH_TOKEN=replace-with-the-same-token-for-local-frontend-use
PUBLIC_READY_HEALTH=false
CORS_ALLOWED_ORIGINS=http://localhost:5173
ALLOW_WILDCARD_CORS=false
```

Production defaults to local PostgreSQL. Keep `DATABASE_BACKEND=postgres` unless you are intentionally using Supabase REST:

```env
DATABASE_BACKEND=postgres
POSTGRES_DB=fundamentracker
POSTGRES_USER=fundamentracker
POSTGRES_PASSWORD=replace-with-a-strong-password
DATABASE_URL=postgresql://fundamentracker:replace-with-a-strong-password@postgres:5432/fundamentracker
```

If the PostgreSQL password contains special URL characters, URL-encode it in `DATABASE_URL`.

The local PostgreSQL schema in `db/init/001_schema.sql` is applied automatically when the production PostgreSQL container initializes an empty data directory.

To keep using existing Supabase REST persistence instead, set the backend explicitly and provide Supabase credentials:

```env
DATABASE_BACKEND=supabase_rest
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-service-or-rest-key
```

For production exposure, keep the API bound to localhost unless you intentionally expose it through your LAN or a reverse proxy:

```env
API_BIND_IP=127.0.0.1
API_PORT=8000
FRONTEND_BIND_IP=127.0.0.1
PROD_FRONTEND_PORT=8080
PUBLIC_API_URL=http://127.0.0.1:8000
```

Optional integrations can stay blank until needed:

```env
GEMINI_API_KEY=
TELEGRAM_TOKEN=
TELEGRAM_CHAT_ID=
TUNNEL_TOKEN=
SEC_USER_AGENT=FundamenTracker contact@example.com
```

Never commit `.env`.

The watchdog defaults to recovering only the required API service:

```env
WATCHDOG_SERVICES=api
```

If this host uses the production Cloudflare Tunnel profile, opt in to recovering both services:

```env
WATCHDOG_SERVICES="api cloudflared"
```

## 5. Start Development

Development mode uses bind mounts, FastAPI reload, and the Vite development server.

Validate the compose file:

```bash
cd /opt/fundamentracker
docker compose -f docker-compose.dev.yml config
```

Start the API and frontend:

```bash
docker compose -f docker-compose.dev.yml up --build api frontend
```

If `DATABASE_BACKEND=postgres`, start the PostgreSQL service first:

```bash
docker compose -f docker-compose.prod.yml up -d postgres
docker compose -f docker-compose.dev.yml up --build api frontend
```

Open:

```text
Frontend: http://localhost:5173
API:      http://localhost:8000
```

Stop development containers:

```bash
docker compose -f docker-compose.dev.yml down
```

The development compose file also defines `cloudflared`, but most local development does not need it. Start it only after setting `TUNNEL_TOKEN`:

```bash
docker compose -f docker-compose.dev.yml up -d cloudflared
```

## 6. Start Production with Docker Compose

Production mode does not use source bind mounts or FastAPI reload. It uses `restart: unless-stopped` and API health checks.

Validate the production compose file:

```bash
cd /opt/fundamentracker
docker compose -f docker-compose.prod.yml config
```

Start the default production services. This starts `postgres` and `api`.

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Check container status:

```bash
docker compose -f docker-compose.prod.yml ps
```

Optional: include the production frontend served by nginx:

```bash
docker compose -f docker-compose.prod.yml --profile frontend up -d --build
```

Open the production frontend on the host:

```text
http://127.0.0.1:8080
```

Optional: include Cloudflare Tunnel after setting `TUNNEL_TOKEN`:

```bash
docker compose -f docker-compose.prod.yml --profile tunnel up -d
```

Tunnel deployments should also set the watchdog service list so a failed public health check can recover the tunnel container:

```env
WATCHDOG_SERVICES="api cloudflared"
```

Stop production containers without deleting data:

```bash
docker compose -f docker-compose.prod.yml down
```

Do not run `docker compose down -v` unless you intentionally want to remove Docker volumes. Local PostgreSQL data is stored under `/srv/fundamentracker/postgres` by default and should be preserved.

## 7. Install systemd

Use systemd when this host should start FundamenTracker automatically on boot.

The installer requires:

```text
/opt/fundamentracker
/opt/fundamentracker/.env
/opt/fundamentracker/docker-compose.prod.yml
/opt/fundamentracker/scripts/watchdog.sh
```

Install and start the main service plus watchdog timer:

```bash
cd /opt/fundamentracker
sudo ./scripts/install-systemd.sh
```

The installer enables:

```text
fundamentracker.service
fundamentracker-watchdog.timer
```

Check status:

```bash
sudo systemctl status fundamentracker.service
sudo systemctl status fundamentracker-watchdog.timer
sudo systemctl list-timers fundamentracker-watchdog.timer
```

Restart after changing `.env` or pulling new code:

```bash
cd /opt/fundamentracker
docker compose -f docker-compose.prod.yml build
sudo systemctl restart fundamentracker.service
```

Uninstall systemd units without deleting project files or data:

```bash
cd /opt/fundamentracker
sudo ./scripts/uninstall-systemd.sh
```

## 8. Check Health

Use `live` to check that the API process is running:

```bash
curl -fsS http://127.0.0.1:8000/health/live | jq
```

Use `ready` to check API readiness and database connectivity:

```bash
source .env
curl -fsS -H "Authorization: Bearer $API_AUTH_TOKEN" http://127.0.0.1:8000/health/ready | jq
```

Expected `live` shape:

```json
{
  "status": "ok",
  "service": "fundamentracker-api",
  "timestamp": "..."
}
```

Expected `ready` shape includes:

```json
{
  "status": "ok",
  "checks": {
    "configuration": {
      "status": "ok"
    },
    "database": {
      "status": "ok"
    }
  }
}
```

If `live` works but `ready` fails, focus on `.env` and the configured database backend.

Repository and compose sanity checks:

```bash
cd /opt/fundamentracker
git status --short
docker compose -f docker-compose.dev.yml config > /tmp/fundamentracker-dev-compose.yml
docker compose -f docker-compose.prod.yml config > /tmp/fundamentracker-prod-compose.yml
docker compose -f docker-compose.prod.yml ps
```

## 9. Access the DB Dashboard

The production compose file includes pgAdmin behind the `dashboard` profile. Use it for local PostgreSQL administration.

Start pgAdmin:

```bash
cd /opt/fundamentracker
docker compose -f docker-compose.prod.yml --profile dashboard up -d pgadmin
```

By default it binds to localhost:

```text
http://127.0.0.1:5050
```

Log in with the values from `.env`:

```env
PGADMIN_DEFAULT_EMAIL=admin@example.com
PGADMIN_DEFAULT_PASSWORD=replace-with-a-strong-password
```

Create a pgAdmin server connection:

```text
Host name/address: postgres
Port: 5432
Maintenance database: fundamentracker
Username: fundamentracker
Password: your POSTGRES_PASSWORD
```

To access pgAdmin from your workstation through SSH without exposing it publicly:

```bash
ssh -L 5050:127.0.0.1:5050 your-user@your-host
```

Then open this on your workstation:

```text
http://127.0.0.1:5050
```

Do not expose pgAdmin through a public tunnel. If LAN access is required, set `PGADMIN_BIND_IP` to a specific LAN IP, not `0.0.0.0`, and protect it with firewall rules.

Supabase users should use the Supabase dashboard for database administration. The local pgAdmin container is for the local PostgreSQL service.

## 10. View Logs

The API writes JSON logs to stdout. Set `LOG_LEVEL` in `.env` to `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL`, then restart the API after changing it:

```bash
cd /opt/fundamentracker
grep '^LOG_LEVEL=' .env
sudo systemctl restart fundamentracker.service
```

Docker Compose logs:

```bash
cd /opt/fundamentracker
docker compose -f docker-compose.prod.yml logs --tail=100
docker compose -f docker-compose.prod.yml logs -f api
docker compose -f docker-compose.prod.yml logs -f postgres
```

Filter API logs with `jq` when reading Docker output:

```bash
docker compose -f docker-compose.prod.yml logs --no-log-prefix api \
  | jq -r 'select(.ticker=="AAPL" or .alert_id=="alert-id" or .provider=="yfinance")'
```

Optional service logs:

```bash
docker compose -f docker-compose.prod.yml logs -f frontend
docker compose -f docker-compose.prod.yml logs -f pgadmin
docker compose -f docker-compose.prod.yml logs -f cloudflared
```

systemd logs:

```bash
sudo journalctl -u fundamentracker.service -n 100 --no-pager
sudo journalctl -u fundamentracker.service -f
```

Watchdog logs:

```bash
sudo journalctl -u fundamentracker-watchdog.service -n 100 --no-pager
sudo journalctl -u fundamentracker-watchdog.service -f
```

Docker daemon logs:

```bash
sudo journalctl -u docker.service -n 100 --no-pager
```

## 11. Backups

Backups are your responsibility. Make them before upgrades and before any schema or persistence changes.

Create a backup directory:

```bash
sudo install -d -m 0750 -o "$USER" -g "$USER" /srv/fundamentracker/backups
```

Back up local PostgreSQL:

```bash
cd /opt/fundamentracker
docker compose -f docker-compose.prod.yml exec -T postgres \
  sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' \
  > "/srv/fundamentracker/backups/fundamentracker-$(date +%Y%m%d-%H%M%S).dump"
```

List backups:

```bash
ls -lh /srv/fundamentracker/backups
```

Restore local PostgreSQL only when you intentionally want to replace current database contents. Stop the API first so it does not write during restore:

```bash
cd /opt/fundamentracker
docker compose -f docker-compose.prod.yml stop api
docker compose -f docker-compose.prod.yml exec -T postgres \
  sh -c 'pg_restore --clean --if-exists -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
  < /srv/fundamentracker/backups/your-backup-file.dump
docker compose -f docker-compose.prod.yml up -d api
```

For Supabase, use Supabase's dashboard, CLI, or provider-native backup tooling. Do not assume the local PostgreSQL backup commands protect Supabase data.

Suggested backup routine:

```bash
# Before application upgrades
cd /opt/fundamentracker
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml exec -T postgres \
  sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' \
  > "/srv/fundamentracker/backups/pre-upgrade-$(date +%Y%m%d-%H%M%S).dump"
```

Copy backups off the host regularly:

```bash
rsync -av /srv/fundamentracker/backups/ your-user@backup-host:/path/to/fundamentracker-backups/
```

## 12. Troubleshooting

### Docker command not found

Install Docker Engine and the Compose plugin, then verify:

```bash
docker --version
docker compose version
sudo systemctl status docker
```

### Permission denied when running Docker

Use `sudo` or add your user to the Docker group:

```bash
sudo usermod -aG docker "$USER"
newgrp docker
docker ps
```

### Production service will not start

Check systemd and container logs:

```bash
sudo systemctl status fundamentracker.service
sudo journalctl -u fundamentracker.service -n 100 --no-pager
cd /opt/fundamentracker
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs --tail=200 api
```

### API live health works but ready health fails

Check persistence configuration:

```bash
cd /opt/fundamentracker
grep -E '^(DATABASE_BACKEND|SUPABASE_URL|DATABASE_URL|POSTGRES_DB|POSTGRES_USER)=' .env
docker compose -f docker-compose.prod.yml ps postgres
docker compose -f docker-compose.prod.yml logs --tail=100 postgres
```

For `DATABASE_BACKEND=postgres`, make sure `DATABASE_URL` points to host `postgres` and port `5432` from inside Compose.

For `DATABASE_BACKEND=supabase_rest`, make sure `SUPABASE_URL` and `SUPABASE_KEY` are valid and that the host can reach Supabase.

### Frontend cannot call the API

Check that the frontend build received the correct API URL and that CORS allows the browser origin:

```bash
cd /opt/fundamentracker
grep -E '^(PUBLIC_API_URL|VITE_API_URL|CORS_ALLOWED_ORIGINS|ALLOW_WILDCARD_CORS)=' .env
curl -fsS http://127.0.0.1:8000/health/live | jq
```

For local development, use:

```env
CORS_ALLOWED_ORIGINS=http://localhost:5173
VITE_API_URL=http://localhost:8000
```

For production behind a domain, use exact origins:

```env
CORS_ALLOWED_ORIGINS=https://your-frontend.example.com
PUBLIC_API_URL=https://your-api.example.com
```

### API returns 401

Mutable endpoints and sensitive read endpoints require:

```text
Authorization: Bearer <API_AUTH_TOKEN>
```

Make sure `.env` contains matching backend and frontend tokens for your deployment:

```env
API_AUTH_TOKEN=replace-with-a-long-random-token
VITE_API_AUTH_TOKEN=replace-with-the-same-token-when-using-the-bundled-frontend
```

### pgAdmin is not reachable

Confirm the dashboard profile is running:

```bash
cd /opt/fundamentracker
docker compose -f docker-compose.prod.yml --profile dashboard ps
docker compose -f docker-compose.prod.yml logs --tail=100 pgadmin
```

Confirm the bind address:

```bash
grep -E '^(PGADMIN_BIND_IP|PGADMIN_PORT)=' /opt/fundamentracker/.env
```

Default URL:

```text
http://127.0.0.1:5050
```

### Cloudflare Tunnel does not start

Check that `TUNNEL_TOKEN` is set and then inspect logs:

```bash
cd /opt/fundamentracker
grep '^TUNNEL_TOKEN=' .env
docker compose -f docker-compose.prod.yml --profile tunnel logs --tail=100 cloudflared
```

Do not paste tunnel tokens into tickets, logs, screenshots, or commits.

### Watchdog keeps restarting services

Check the configured health URL:

```bash
cd /opt/fundamentracker
grep '^PUBLIC_HEALTH_URL=' .env
grep '^WATCHDOG_SERVICES=' .env
sudo journalctl -u fundamentracker-watchdog.service -n 100 --no-pager
health_url="$(grep '^PUBLIC_HEALTH_URL=' .env | cut -d= -f2-)"
api_auth_token="$(grep '^API_AUTH_TOKEN=' .env | cut -d= -f2-)"
curl -v -H "Authorization: Bearer ${api_auth_token}" "${health_url:-http://127.0.0.1:8000/health/ready}"
```

If `PUBLIC_HEALTH_URL` is empty, the watchdog checks:

```text
http://127.0.0.1:8000/health/ready
```

If `WATCHDOG_SERVICES` is empty, the watchdog recovers only `api`. Set `WATCHDOG_SERVICES="api cloudflared"` only on hosts that run the production tunnel profile.

Use `docs/WATCHDOG.md` for more watchdog-specific operations.

### After pulling updates

Back up first, then rebuild and restart:

```bash
cd /opt/fundamentracker
git pull --ff-only
docker compose -f docker-compose.prod.yml build
sudo systemctl restart fundamentracker.service
source .env
curl -fsS -H "Authorization: Bearer $API_AUTH_TOKEN" http://127.0.0.1:8000/health/ready | jq
```

If you are not using systemd:

```bash
cd /opt/fundamentracker
git pull --ff-only
docker compose -f docker-compose.prod.yml up -d --build
source .env
curl -fsS -H "Authorization: Bearer $API_AUTH_TOKEN" http://127.0.0.1:8000/health/ready | jq
```
