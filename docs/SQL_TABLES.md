# SQL Tables

The local PostgreSQL bootstrap schema lives in `db/init/001_schema.sql`.

For an existing local PostgreSQL database, apply migrations in order:

```bash
psql "$DATABASE_URL" -f db/migrations/002_metric_cache_provider_health.sql
```

For Supabase REST mode, run equivalent SQL in the Supabase SQL editor. The tables currently used by the app are:

```sql
CREATE TABLE tickers (
  symbol VARCHAR PRIMARY KEY,
  name VARCHAR NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE alerts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ticker_symbol VARCHAR REFERENCES tickers(symbol) ON DELETE CASCADE,
  metric VARCHAR NOT NULL,
  operator VARCHAR NOT NULL,
  target_value NUMERIC NOT NULL,
  is_active BOOLEAN DEFAULT TRUE,
  is_triggered BOOLEAN DEFAULT FALSE,
  reference_value NUMERIC,
  alert_type VARCHAR DEFAULT 'absolute',
  current_value NUMERIC,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE alert_history (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  alert_id UUID REFERENCES alerts(id) ON DELETE CASCADE,
  triggered_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  trigger_value NUMERIC NOT NULL,
  target_value NUMERIC NOT NULL
);

CREATE TABLE scan_settings (
  id INT PRIMARY KEY DEFAULT 1,
  interval_seconds INT DEFAULT 0,
  last_scan_time INT DEFAULT 0
);

INSERT INTO scan_settings (id, interval_seconds, last_scan_time)
VALUES (1, 0, 0)
ON CONFLICT (id) DO NOTHING;

CREATE TABLE metric_snapshots (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  symbol VARCHAR NOT NULL,
  metric VARCHAR NOT NULL,
  value NUMERIC,
  unit VARCHAR,
  currency VARCHAR,
  source VARCHAR NOT NULL,
  as_of_date DATE,
  fetched_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
  confidence NUMERIC,
  raw_payload JSONB
);

CREATE INDEX idx_metric_snapshots_lookup
  ON metric_snapshots(symbol, metric, fetched_at DESC);
CREATE INDEX idx_metric_snapshots_freshness
  ON metric_snapshots(symbol, metric, expires_at DESC);
CREATE INDEX idx_metric_snapshots_source
  ON metric_snapshots(source, fetched_at DESC);

CREATE TABLE provider_health (
  provider VARCHAR PRIMARY KEY,
  status VARCHAR NOT NULL,
  last_ok_at TIMESTAMP WITH TIME ZONE,
  last_error_at TIMESTAMP WITH TIME ZONE,
  last_error TEXT
);

CREATE INDEX idx_provider_health_lookup
  ON provider_health(status);
```
