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
