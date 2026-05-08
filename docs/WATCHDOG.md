# Watchdog

FundamenTracker includes a local systemd watchdog that periodically checks the API health endpoint and attempts a conservative container recovery when the app stops responding.

The watchdog never deletes Docker volumes, database files, images, or application data. It only runs targeted `restart` and `up -d --force-recreate` commands for the `api` and `cloudflared` services.

## Health URL

The watchdog reads `PUBLIC_HEALTH_URL` from `/opt/fundamentracker/.env`.

Example public Cloudflare URL:

```env
PUBLIC_HEALTH_URL=https://fundamentracker.example.com/health/ready
```

Example local URL:

```env
PUBLIC_HEALTH_URL=http://127.0.0.1:8000/health/ready
```

If `PUBLIC_HEALTH_URL` is not set, the default is:

```text
http://127.0.0.1:8000/health/ready
```

Use the local URL when you only want to verify the API container on the host. Use the public Cloudflare URL when you also want to verify tunnel reachability.

## Optional Settings

These can be placed in `.env`:

```env
WATCHDOG_RECHECK_WAIT_SECONDS=30
WATCHDOG_CURL_TIMEOUT_SECONDS=10
```

`WATCHDOG_RECHECK_WAIT_SECONDS` controls how long the script waits after a restart or recreate before checking health again.

`WATCHDOG_CURL_TIMEOUT_SECONDS` controls the maximum duration of each `curl` health request.

## Recovery Behavior

On each timer run, `scripts/watchdog.sh`:

1. Checks the configured health URL with `curl --fail`.
2. If the check fails, restarts only the `api` and `cloudflared` services:

```bash
docker compose -f docker-compose.prod.yml restart api cloudflared
```

3. Waits for `WATCHDOG_RECHECK_WAIT_SECONDS`.
4. If the check still fails, recreates only the `api` and `cloudflared` services:

```bash
docker compose -f docker-compose.prod.yml up -d --force-recreate api cloudflared
```

5. Waits again and exits with an error if the health check is still failing.

The script does not run `docker compose down -v`, `docker volume rm`, database reset commands, or prune commands.

## Install

Install the main service and watchdog timer from the production checkout:

```bash
cd /opt/fundamentracker
sudo ./scripts/install-systemd.sh
```

The installer copies these units into `/etc/systemd/system/`:

```text
fundamentracker.service
fundamentracker-watchdog.service
fundamentracker-watchdog.timer
```

It then enables and starts `fundamentracker.service` and `fundamentracker-watchdog.timer`.

The timer runs once two minutes after boot and then every five minutes:

```ini
OnBootSec=2min
OnUnitActiveSec=5min
```

## Operations

Check timer status:

```bash
sudo systemctl status fundamentracker-watchdog.timer
sudo systemctl list-timers fundamentracker-watchdog.timer
```

Run the watchdog manually:

```bash
cd /opt/fundamentracker
sudo ./scripts/watchdog.sh
```

View watchdog logs:

```bash
sudo journalctl -u fundamentracker-watchdog.service -n 100 --no-pager
sudo journalctl -u fundamentracker-watchdog.service -f
```

Disable the watchdog without stopping the main app:

```bash
sudo systemctl disable --now fundamentracker-watchdog.timer
```

Re-enable it:

```bash
sudo systemctl enable --now fundamentracker-watchdog.timer
```

## Uninstall

To remove the systemd service and watchdog units:

```bash
cd /opt/fundamentracker
sudo ./scripts/uninstall-systemd.sh
```

This does not delete project files, `.env`, Docker images, volumes, or persisted application data.
