CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS metric_snapshots (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  symbol VARCHAR,
  metric VARCHAR NOT NULL,
  value NUMERIC,
  unit VARCHAR,
  currency VARCHAR,
  source VARCHAR NOT NULL,
  as_of_date DATE,
  fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMPTZ,
  confidence NUMERIC,
  raw_payload JSONB
);

ALTER TABLE metric_snapshots ADD COLUMN IF NOT EXISTS symbol VARCHAR;
ALTER TABLE metric_snapshots ADD COLUMN IF NOT EXISTS unit VARCHAR;
ALTER TABLE metric_snapshots ADD COLUMN IF NOT EXISTS currency VARCHAR;
ALTER TABLE metric_snapshots ADD COLUMN IF NOT EXISTS as_of_date DATE;
ALTER TABLE metric_snapshots ADD COLUMN IF NOT EXISTS fetched_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE metric_snapshots ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ;
ALTER TABLE metric_snapshots ADD COLUMN IF NOT EXISTS confidence NUMERIC;
ALTER TABLE metric_snapshots ADD COLUMN IF NOT EXISTS raw_payload JSONB;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_name = 'metric_snapshots'
      AND column_name = 'ticker_symbol'
  ) THEN
    EXECUTE 'UPDATE metric_snapshots SET symbol = COALESCE(symbol, ticker_symbol)';
  END IF;
END $$;

UPDATE metric_snapshots
SET expires_at = COALESCE(expires_at, fetched_at + INTERVAL '1 day', NOW() + INTERVAL '1 day')
WHERE expires_at IS NULL;

ALTER TABLE metric_snapshots ALTER COLUMN fetched_at SET NOT NULL;
ALTER TABLE metric_snapshots ALTER COLUMN expires_at SET NOT NULL;

CREATE INDEX IF NOT EXISTS idx_metric_snapshots_symbol_metric_fetched_at
  ON metric_snapshots(symbol, metric, fetched_at DESC);
CREATE INDEX IF NOT EXISTS idx_metric_snapshots_symbol_metric_expires_at
  ON metric_snapshots(symbol, metric, expires_at DESC);
CREATE INDEX IF NOT EXISTS idx_metric_snapshots_source_fetched_at
  ON metric_snapshots(source, fetched_at DESC);

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_name = 'provider_health'
      AND column_name = 'provider_name'
  )
  AND NOT EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_name = 'provider_health'
      AND column_name = 'provider'
  ) THEN
    ALTER TABLE provider_health RENAME TO provider_health_events;
  END IF;
END $$;

CREATE TABLE IF NOT EXISTS provider_health (
  provider VARCHAR PRIMARY KEY,
  status VARCHAR NOT NULL,
  last_ok_at TIMESTAMPTZ,
  last_error_at TIMESTAMPTZ,
  last_error TEXT
);

ALTER TABLE provider_health ADD COLUMN IF NOT EXISTS last_ok_at TIMESTAMPTZ;
ALTER TABLE provider_health ADD COLUMN IF NOT EXISTS last_error_at TIMESTAMPTZ;
ALTER TABLE provider_health ADD COLUMN IF NOT EXISTS last_error TEXT;

CREATE INDEX IF NOT EXISTS idx_provider_health_status
  ON provider_health(status);
