CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS tickers (
  symbol VARCHAR PRIMARY KEY,
  name VARCHAR NOT NULL,
  status VARCHAR DEFAULT 'watching',
  priority VARCHAR DEFAULT 'medium',
  notes TEXT,
  thesis TEXT,
  target_action VARCHAR,
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS tags (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR NOT NULL UNIQUE,
  color VARCHAR,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ticker_tags (
  ticker_symbol VARCHAR REFERENCES tickers(symbol) ON DELETE CASCADE,
  tag_id UUID REFERENCES tags(id) ON DELETE CASCADE,
  PRIMARY KEY (ticker_symbol, tag_id)
);

CREATE INDEX IF NOT EXISTS idx_ticker_tags_tag_id ON ticker_tags(tag_id);

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
  current_source VARCHAR,
  current_as_of_date DATE,
  current_fetched_at TIMESTAMPTZ,
  current_expires_at TIMESTAMPTZ,
  current_stale BOOLEAN,
  current_confidence NUMERIC,
  deleted_at TIMESTAMPTZ,
  restored_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alerts_ticker_symbol ON alerts(ticker_symbol);
CREATE INDEX IF NOT EXISTS idx_alerts_active ON alerts(is_active);
CREATE INDEX IF NOT EXISTS idx_alerts_deleted_at ON alerts(deleted_at);

CREATE TABLE IF NOT EXISTS alert_history (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  alert_id UUID REFERENCES alerts(id) ON DELETE SET NULL,
  triggered_at TIMESTAMPTZ DEFAULT NOW(),
  trigger_value NUMERIC NOT NULL,
  target_value NUMERIC NOT NULL,
  ticker_symbol VARCHAR,
  company_name VARCHAR,
  metric VARCHAR,
  operator VARCHAR,
  alert_type VARCHAR,
  reference_value NUMERIC,
  current_value NUMERIC,
  source VARCHAR,
  as_of_date DATE,
  fetched_at TIMESTAMPTZ,
  message TEXT
);

CREATE INDEX IF NOT EXISTS idx_alert_history_triggered_at ON alert_history(triggered_at DESC);
CREATE INDEX IF NOT EXISTS idx_alert_history_alert_id ON alert_history(alert_id);

CREATE TABLE IF NOT EXISTS signals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ticker_symbol VARCHAR,
  company_name VARCHAR,
  signal_type VARCHAR NOT NULL,
  severity VARCHAR DEFAULT 'info',
  title VARCHAR NOT NULL,
  message TEXT,
  metric VARCHAR,
  current_value NUMERIC,
  previous_value NUMERIC,
  target_value NUMERIC,
  source VARCHAR,
  as_of_date DATE,
  fetched_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  acknowledged_at TIMESTAMPTZ,
  dismissed_at TIMESTAMPTZ,
  raw_payload JSONB
);

CREATE INDEX IF NOT EXISTS idx_signals_open
  ON signals(created_at DESC)
  WHERE acknowledged_at IS NULL AND dismissed_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_signals_ticker_symbol ON signals(ticker_symbol);
CREATE INDEX IF NOT EXISTS idx_signals_signal_type ON signals(signal_type);

CREATE TABLE IF NOT EXISTS scan_settings (
  id INT PRIMARY KEY DEFAULT 1,
  interval_seconds INT DEFAULT 0,
  last_scan_time INT DEFAULT 0
);

INSERT INTO scan_settings (id, interval_seconds, last_scan_time)
VALUES (1, 0, 0)
ON CONFLICT (id) DO NOTHING;

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

CREATE TABLE IF NOT EXISTS provider_health (
  provider VARCHAR PRIMARY KEY,
  status VARCHAR NOT NULL,
  last_ok_at TIMESTAMPTZ,
  last_error_at TIMESTAMPTZ,
  last_error TEXT
);

CREATE INDEX IF NOT EXISTS idx_provider_health_lookup
  ON provider_health(status);
