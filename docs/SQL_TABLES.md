# SQL Tables

The local PostgreSQL bootstrap schema lives in:

```text
db/init/001_schema.sql
```

It is applied automatically only when the production PostgreSQL container
initializes an empty data directory.

Migrations for existing local PostgreSQL databases live in:

```text
db/migrations/*.sql
```

Apply pending migrations with:

```bash
make db-migrate
```

Preview pending migrations without applying:

```bash
./scripts/migrate-db.sh --dry-run
```

For Supabase REST mode, run equivalent SQL manually in the Supabase SQL editor
when a schema change is required. The migration runner targets PostgreSQL.

## Current Bootstrap Schema

The app currently uses these tables.

### `tickers`

```sql
CREATE TABLE IF NOT EXISTS tickers (
  symbol VARCHAR PRIMARY KEY,
  name VARCHAR NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### `alerts`

```sql
CREATE TABLE IF NOT EXISTS alerts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ticker_symbol VARCHAR NOT NULL REFERENCES tickers(symbol) ON DELETE CASCADE,
  metric VARCHAR NOT NULL,
  operator VARCHAR NOT NULL,
  target_value NUMERIC NOT NULL,
  is_active BOOLEAN DEFAULT TRUE,
  is_triggered BOOLEAN DEFAULT FALSE,
  reference_value NUMERIC,
  alert_type VARCHAR DEFAULT 'absolute',
  current_value NUMERIC,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alerts_ticker_symbol ON alerts(ticker_symbol);
CREATE INDEX IF NOT EXISTS idx_alerts_active ON alerts(is_active);
```

`alerts.id` is the canonical alert identity. Do not rely on
`ticker_symbol + metric` as a unique identifier.

### `alert_history`

```sql
CREATE TABLE IF NOT EXISTS alert_history (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  alert_id UUID NOT NULL REFERENCES alerts(id) ON DELETE CASCADE,
  triggered_at TIMESTAMPTZ DEFAULT NOW(),
  trigger_value NUMERIC NOT NULL,
  target_value NUMERIC NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_alert_history_triggered_at
  ON alert_history(triggered_at DESC);
CREATE INDEX IF NOT EXISTS idx_alert_history_alert_id
  ON alert_history(alert_id);
```

### `scan_settings`

```sql
CREATE TABLE IF NOT EXISTS scan_settings (
  id INT PRIMARY KEY DEFAULT 1,
  interval_seconds INT DEFAULT 0,
  last_scan_time INT DEFAULT 0
);

INSERT INTO scan_settings (id, interval_seconds, last_scan_time)
VALUES (1, 0, 0)
ON CONFLICT (id) DO NOTHING;
```

### `data_providers`

```sql
CREATE TABLE IF NOT EXISTS data_providers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR NOT NULL UNIQUE,
  provider_type VARCHAR NOT NULL DEFAULT 'market_data',
  is_enabled BOOLEAN DEFAULT TRUE,
  priority INT DEFAULT 100,
  config JSONB DEFAULT '{}'::JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

Known limitation: this table is created by the bootstrap schema but is not
currently used by `MarketDataService` provider selection.

### `metric_snapshots`

```sql
CREATE TABLE IF NOT EXISTS metric_snapshots (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  symbol VARCHAR NOT NULL,
  metric VARCHAR NOT NULL,
  value NUMERIC,
  unit VARCHAR,
  currency VARCHAR,
  source VARCHAR NOT NULL,
  as_of_date DATE,
  fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMPTZ NOT NULL,
  confidence NUMERIC,
  raw_payload JSONB
);

CREATE INDEX IF NOT EXISTS idx_metric_snapshots_lookup
  ON metric_snapshots(symbol, metric, fetched_at DESC);
CREATE INDEX IF NOT EXISTS idx_metric_snapshots_freshness
  ON metric_snapshots(symbol, metric, expires_at DESC);
CREATE INDEX IF NOT EXISTS idx_metric_snapshots_source
  ON metric_snapshots(source, fetched_at DESC);
```

`MarketDataService` uses this table for fresh cache hits and stale fallback.
History snapshots use metric keys such as `price_history:1y` and
`metric_history:pe:1y`.

### `provider_health`

```sql
CREATE TABLE IF NOT EXISTS provider_health (
  provider VARCHAR PRIMARY KEY,
  status VARCHAR NOT NULL,
  last_ok_at TIMESTAMPTZ,
  last_error_at TIMESTAMPTZ,
  last_error TEXT
);

CREATE INDEX IF NOT EXISTS idx_provider_health_lookup
  ON provider_health(status);
```

The protected endpoint `GET /data/providers/health` returns rows from this
table. `GET /ops/status` summarizes provider status without exposing raw
provider error text.

### `schema_migrations`

`schema_migrations` is created by `api/db/migration_runner.py`, not by the
bootstrap schema. It records migration file name, checksum, and application
timestamp so already-applied migrations are skipped safely.

## Current Migration Files

- `db/migrations/002_metric_cache_provider_health.sql`: adds or updates
  `metric_snapshots` and `provider_health` for existing local PostgreSQL
  databases, including compatibility handling for older metric snapshot shapes.
