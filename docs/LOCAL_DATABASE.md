# Local PostgreSQL

FundamenTracker supports two persistence backends:

```env
DATABASE_BACKEND=supabase_rest
DATABASE_BACKEND=postgres
```

Use `supabase_rest` to keep the existing Supabase REST behavior. Use `postgres` for the local PostgreSQL service in `docker-compose.prod.yml`.

## Configure PostgreSQL

Copy `.env.example` to `.env` and set strong local values:

```env
DATABASE_BACKEND=postgres
POSTGRES_DB=fundamentracker
POSTGRES_USER=fundamentracker
POSTGRES_PASSWORD=replace-with-a-strong-password
DATABASE_URL=postgresql://fundamentracker:replace-with-a-strong-password@postgres:5432/fundamentracker
```

URL-encode special characters in `POSTGRES_PASSWORD` when copying it into `DATABASE_URL`.

The production Compose file stores PostgreSQL data in:

```text
${FT_DATA_DIR:-/srv/fundamentracker}/postgres
```

To use another host data directory:

```env
FT_DATA_DIR=/srv/fundamentracker
```

The schema in `db/init/001_schema.sql` is applied automatically only when PostgreSQL initializes an empty data directory. Existing data is not recreated or reset by normal `docker compose up` runs.

## Apply Migrations

For an existing PostgreSQL data directory, apply schema migrations without recreating the database:

```bash
docker compose -f docker-compose.prod.yml exec -T postgres \
  psql -U "${POSTGRES_USER:-fundamentracker}" -d "${POSTGRES_DB:-fundamentracker}" \
  < db/migrations/002_metric_cache_provider_health.sql
```

If you are running `psql` from the repository on the host instead of inside the container:

```bash
psql "$DATABASE_URL" -f db/migrations/002_metric_cache_provider_health.sql
```

Start the production stack:

```bash
docker compose -f docker-compose.prod.yml up -d
```

Check PostgreSQL health:

```bash
docker compose -f docker-compose.prod.yml ps postgres
```

Check API readiness:

```bash
curl http://127.0.0.1:8000/health/ready
```

When `DATABASE_BACKEND=postgres`, the API waits for PostgreSQL during startup before starting background scanners or Telegram polling.

## Dashboard Access

The production Compose file includes pgAdmin behind the `dashboard` profile. Start it with:

```bash
docker compose -f docker-compose.prod.yml --profile dashboard up -d pgadmin
```

By default, pgAdmin binds only to localhost:

```env
PGADMIN_BIND_IP=127.0.0.1
PGADMIN_DEFAULT_EMAIL=admin@example.com
PGADMIN_DEFAULT_PASSWORD=replace-with-a-strong-password
```

Open it on the host:

```text
http://127.0.0.1:5050
```

Add a pgAdmin server connection with:

```text
Host name/address: postgres
Port: 5432
Maintenance database: fundamentracker
Username: fundamentracker
Password: your POSTGRES_PASSWORD
```

## LAN Dashboard Access

To access pgAdmin from another device on your LAN, bind it to the host's LAN IP instead of all interfaces:

```env
PGADMIN_BIND_IP=192.168.1.50
```

Then restart pgAdmin:

```bash
docker compose -f docker-compose.prod.yml --profile dashboard up -d pgadmin
```

Open:

```text
http://192.168.1.50:5050
```

Do not expose pgAdmin through a public Cloudflare Tunnel. If LAN access is needed, use a private LAN IP, firewall rules, SSH, or a VPN.

## Supabase Compatibility

To keep using Supabase REST, leave:

```env
DATABASE_BACKEND=supabase_rest
SUPABASE_URL=https://example-project.supabase.co
SUPABASE_KEY=example-supabase-key
```

The local PostgreSQL service can exist in the production Compose file without changing the API persistence mode. The API uses PostgreSQL only when `DATABASE_BACKEND=postgres`.
