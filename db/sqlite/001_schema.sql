PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS tickers (
  symbol TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  status TEXT DEFAULT 'watching',
  priority TEXT DEFAULT 'medium',
  notes TEXT,
  thesis TEXT,
  target_action TEXT,
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS tags (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  color TEXT,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS ticker_tags (
  ticker_symbol TEXT NOT NULL REFERENCES tickers(symbol) ON DELETE CASCADE,
  tag_id TEXT NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
  PRIMARY KEY (ticker_symbol, tag_id)
);
CREATE INDEX IF NOT EXISTS idx_ticker_tags_tag_id ON ticker_tags(tag_id);

CREATE TABLE IF NOT EXISTS alerts (
  id TEXT PRIMARY KEY,
  ticker_symbol TEXT NOT NULL REFERENCES tickers(symbol) ON DELETE CASCADE,
  metric TEXT NOT NULL,
  operator TEXT NOT NULL,
  target_value REAL NOT NULL,
  is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
  is_triggered INTEGER NOT NULL DEFAULT 0 CHECK (is_triggered IN (0, 1)),
  reference_value REAL,
  alert_type TEXT DEFAULT 'absolute',
  current_value REAL,
  current_source TEXT,
  current_as_of_date TEXT,
  current_fetched_at TEXT,
  current_expires_at TEXT,
  current_stale INTEGER CHECK (current_stale IS NULL OR current_stale IN (0, 1)),
  current_confidence REAL,
  deleted_at TEXT,
  restored_at TEXT,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_alerts_ticker_symbol ON alerts(ticker_symbol);
CREATE INDEX IF NOT EXISTS idx_alerts_active ON alerts(is_active);
CREATE INDEX IF NOT EXISTS idx_alerts_deleted_at ON alerts(deleted_at);

CREATE TABLE IF NOT EXISTS alert_history (
  id TEXT PRIMARY KEY,
  alert_id TEXT REFERENCES alerts(id) ON DELETE SET NULL,
  triggered_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  trigger_value REAL NOT NULL,
  target_value REAL NOT NULL,
  ticker_symbol TEXT,
  company_name TEXT,
  metric TEXT,
  operator TEXT,
  alert_type TEXT,
  reference_value REAL,
  current_value REAL,
  source TEXT,
  as_of_date TEXT,
  fetched_at TEXT,
  message TEXT
);
CREATE INDEX IF NOT EXISTS idx_alert_history_triggered_at ON alert_history(triggered_at DESC);
CREATE INDEX IF NOT EXISTS idx_alert_history_alert_id ON alert_history(alert_id);

CREATE TABLE IF NOT EXISTS signals (
  id TEXT PRIMARY KEY,
  ticker_symbol TEXT,
  company_name TEXT,
  signal_type TEXT NOT NULL,
  severity TEXT DEFAULT 'info',
  title TEXT NOT NULL,
  message TEXT,
  metric TEXT,
  current_value REAL,
  previous_value REAL,
  target_value REAL,
  source TEXT,
  as_of_date TEXT,
  fetched_at TEXT,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  acknowledged_at TEXT,
  dismissed_at TEXT,
  raw_payload TEXT
);
CREATE INDEX IF NOT EXISTS idx_signals_open
  ON signals(created_at DESC)
  WHERE acknowledged_at IS NULL AND dismissed_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_signals_ticker_symbol ON signals(ticker_symbol);
CREATE INDEX IF NOT EXISTS idx_signals_signal_type ON signals(signal_type);

CREATE TABLE IF NOT EXISTS scan_settings (
  id INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),
  interval_seconds INTEGER DEFAULT 0,
  last_scan_time INTEGER DEFAULT 0
);
INSERT INTO scan_settings (id, interval_seconds, last_scan_time)
VALUES (1, 0, 0)
ON CONFLICT (id) DO NOTHING;

CREATE TABLE IF NOT EXISTS data_providers (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  provider_type TEXT NOT NULL DEFAULT 'market_data',
  is_enabled INTEGER NOT NULL DEFAULT 1 CHECK (is_enabled IN (0, 1)),
  priority INTEGER DEFAULT 100,
  config TEXT DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS metric_snapshots (
  id TEXT PRIMARY KEY,
  symbol TEXT NOT NULL,
  metric TEXT NOT NULL,
  value REAL,
  unit TEXT,
  currency TEXT,
  source TEXT NOT NULL,
  as_of_date TEXT,
  fetched_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  expires_at TEXT NOT NULL,
  confidence REAL,
  raw_payload TEXT
);
CREATE INDEX IF NOT EXISTS idx_metric_snapshots_lookup
  ON metric_snapshots(symbol, metric, fetched_at DESC);
CREATE INDEX IF NOT EXISTS idx_metric_snapshots_freshness
  ON metric_snapshots(symbol, metric, expires_at DESC);
CREATE INDEX IF NOT EXISTS idx_metric_snapshots_source
  ON metric_snapshots(source, fetched_at DESC);

CREATE TABLE IF NOT EXISTS provider_health (
  provider TEXT PRIMARY KEY,
  status TEXT NOT NULL,
  last_ok_at TEXT,
  last_error_at TEXT,
  last_error TEXT
);
CREATE INDEX IF NOT EXISTS idx_provider_health_lookup
  ON provider_health(status);
