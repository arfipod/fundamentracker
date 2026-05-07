# Host Setup

This guide installs FundamenTracker as a systemd-managed Docker Compose service on a Linux host.

The systemd unit expects the production checkout at:

```bash
/opt/fundamentracker
```

The service runs:

```bash
docker compose -f docker-compose.prod.yml up -d --remove-orphans
```

and stops with:

```bash
docker compose -f docker-compose.prod.yml down
```

## Prerequisites

- Docker Engine with the Compose plugin installed.
- A configured production checkout at `/opt/fundamentracker`.
- A production `.env` file at `/opt/fundamentracker/.env`.
- `docker-compose.prod.yml` present in `/opt/fundamentracker`.

Do not put secrets in the systemd unit file. Keep tokens, passwords, and provider keys in `.env`.

## Install

From the repository checkout:

```bash
sudo ./scripts/install-systemd.sh
```

The installer copies `systemd/fundamentracker.service` to `/etc/systemd/system/`, reloads systemd, enables the service at boot, and starts it immediately.

If your checkout is not in `/opt/fundamentracker`, move or copy the project there before installing:

```bash
sudo mkdir -p /opt/fundamentracker
sudo rsync -a ./ /opt/fundamentracker/
cd /opt/fundamentracker
sudo ./scripts/install-systemd.sh
```

## Daily Operation

Check service status:

```bash
sudo systemctl status fundamentracker.service
```

View service logs:

```bash
sudo journalctl -u fundamentracker.service -n 100 --no-pager
sudo journalctl -u fundamentracker.service -f
```

Start, stop, or restart the stack:

```bash
sudo systemctl start fundamentracker.service
sudo systemctl stop fundamentracker.service
sudo systemctl restart fundamentracker.service
```

Check the Docker containers directly:

```bash
cd /opt/fundamentracker
sudo docker compose -f docker-compose.prod.yml ps
sudo docker compose -f docker-compose.prod.yml logs --tail=100
```

## Recovery

Reload systemd after changing the unit file:

```bash
sudo systemctl daemon-reload
sudo systemctl restart fundamentracker.service
```

Rebuild and restart containers after application updates:

```bash
cd /opt/fundamentracker
sudo docker compose -f docker-compose.prod.yml build
sudo systemctl restart fundamentracker.service
```

Recover from a failed service state:

```bash
sudo systemctl reset-failed fundamentracker.service
sudo systemctl restart fundamentracker.service
sudo systemctl status fundamentracker.service
```

Inspect detailed container logs during recovery:

```bash
cd /opt/fundamentracker
sudo docker compose -f docker-compose.prod.yml logs --tail=200 api
sudo docker compose -f docker-compose.prod.yml logs --tail=200 frontend
```

If Docker itself is not running:

```bash
sudo systemctl status docker.service
sudo systemctl restart docker.service
sudo systemctl restart fundamentracker.service
```

## Uninstall

To stop the service, disable boot autostart, remove the installed unit, and reload systemd:

```bash
sudo ./scripts/uninstall-systemd.sh
```

This does not delete project files, `.env`, Docker images, volumes, or persisted application data.
