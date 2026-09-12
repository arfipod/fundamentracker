# Raspberry Pi 1 native deployment

This deployment profile keeps the Vercel frontend unchanged and runs only the
FundamenTracker API plus SQLite on the Raspberry Pi 1. It deliberately avoids
Docker, PostgreSQL, MariaDB, Node, and a local frontend web server.

Target public flow after cut-over:

```text
fundamentracker.vercel.app
        |
        v
api-fundamentracker.arfipod.org
        |
   Cloudflare Tunnel
        |
        v
127.0.0.1:8000 on Raspberry Pi
        |
        v
/srv/fundamentracker/fundamentracker.db
```

The existing public API hostname is retained. Cloudflare is changed only after
the native deployment is proven locally.

## 1. Run the ARMv6 probe first

The Pi 1 is ARMv6 with limited memory. The principal migration risk is the
compiled Python dependency stack, not SQLite. Do not assume PyPI wheels built
for newer ARM variants will run on this machine.

From any checkout on the Pi:

```bash
bash deploy/rpi1/probe-runtime.sh | tee rpi1-runtime-probe.log
```

The probe is intentionally non-destructive. It does not install apt packages,
change services, or retain its temporary virtualenv/downloads. It records:

- OS/kernel/architecture and RAM/swap;
- Python and SQLite versions;
- Raspberry Pi OS package candidates for compiled dependencies;
- existing imports;
- whether the exact current `requirements.txt` is available as wheels for the
  running architecture;
- individual wheel availability for NumPy, pandas, curl_cffi, cffi, lxml,
  pydantic-core, and yfinance;
- current `cloudflared` availability.

Choose the native Python package strategy from this evidence. Do not let pip
silently spend hours compiling large packages on the Pi just to discover that a
wheel is unavailable.

## 2. Keep the deployment Git-managed

The native service expects the checkout at:

```text
/opt/fundamentracker
```

This is intentional. The Raspberry installation remains a normal Git checkout,
so upgrades can be reviewed and pulled instead of copying an opaque second
edition of the application.

For example, after the target branch/release has been approved:

```bash
sudo git clone https://github.com/arfipod/fundamentracker.git /opt/fundamentracker
cd /opt/fundamentracker
sudo git checkout main
```

Do not run two different FundamenTracker implementations from the same SQLite
file.

## 3. Prepare the Python runtime

The exact commands depend on the ARMv6 probe result. The service installer will
refuse to continue until `/opt/fundamentracker/.venv/bin/python` exists and can
import the core runtime (`fastapi`, `uvicorn`, `pandas`, `yfinance`, and
`api.api`).

This guard exists so the deployment does not accidentally install a partially
working service. Once the package strategy is proven on the real Pi, document
and pin it before production cut-over.

## 4. Configure the native service

The installer creates a dedicated `fundamentracker` system user and the
persistent/configuration directories. It never overwrites an existing env file.

Run from `/opt/fundamentracker`:

```bash
sudo bash deploy/rpi1/install-native.sh
```

On the first invocation, edit:

```text
/etc/fundamentracker/fundamentracker.env
```

At minimum, replace the placeholder `API_AUTH_TOKEN`. The supplied template
uses:

```env
DATABASE_BACKEND=sqlite
SQLITE_PATH=/srv/fundamentracker/fundamentracker.db
CORS_ALLOWED_ORIGINS=https://fundamentracker.vercel.app
```

The API listens only on `127.0.0.1:8000` with one Uvicorn worker. The service is
nice'd below interactive/monitoring workloads and given a positive OOM score so
that a pathological API workload is preferred over SSH/system management if
the machine is under severe memory pressure.

## 5. Migrate production data

Use the read-only migration documented in
[`MIGRATING_TO_SQLITE.md`](MIGRATING_TO_SQLITE.md). For a trial migration, keep
the current production mini-PC running and copy its PostgreSQL state to a test
SQLite file.

Before final cut-over:

1. stop periodic scans/writes on the old production instance;
2. make one fresh PostgreSQL -> SQLite migration;
3. place the verified file at
   `/srv/fundamentracker/fundamentracker.db` with owner/group
   `fundamentracker:fundamentracker`;
4. start/restart `fundamentracker-native.service`;
5. validate locally before changing Cloudflare.

## 6. Validate locally

The standard validator does not trigger a scan or mutate application data:

```bash
sudo bash deploy/rpi1/validate-native.sh | tee rpi1-native-validation.log
```

It checks service state, process RSS, SQLite integrity and foreign keys, row
counts, `/health/live`, authenticated `/health/ready`, and an authenticated
watchlist read.

A real scan is deliberately opt-in because it can update alert state, history,
and signals:

```bash
sudo bash deploy/rpi1/validate-native.sh --scan | tee rpi1-scan-validation.log
```

Run that only on a disposable migration copy or when the final migrated copy is
intentionally ready for a real scan.

## 7. Cloudflare cut-over comes last

Keep `api-fundamentracker.arfipod.org`; do not create a second permanent API
hostname. Once local API and scan validation pass, install/configure the
Cloudflare Tunnel connector on the Pi so that the existing hostname reaches:

```text
http://127.0.0.1:8000
```

Cloudflare has shipped Linux ARM builds and its release notes explicitly include
an ARMv6 build fix. Still execute `cloudflared --version` on the actual Pi as
part of the host validation before changing DNS/tunnel routing.

Only then repoint/reuse the existing public hostname and verify the Vercel
frontend end-to-end. Keep the old mini-PC deployment stopped but recoverable for
a short rollback window.

## 8. Dashboard integration is later

The C++ TFT dashboard stays independent of FundamenTracker during this migration.
After the backend is stable, it can query the API over
`http://127.0.0.1:8000` for health, signals, scan state, and explicit actions.
A FundamenTracker crash must not take the dashboard down with it.
