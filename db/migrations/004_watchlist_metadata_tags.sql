CREATE EXTENSION IF NOT EXISTS pgcrypto;

ALTER TABLE tickers ADD COLUMN IF NOT EXISTS status VARCHAR DEFAULT 'watching';
ALTER TABLE tickers ADD COLUMN IF NOT EXISTS priority VARCHAR DEFAULT 'medium';
ALTER TABLE tickers ADD COLUMN IF NOT EXISTS notes TEXT;
ALTER TABLE tickers ADD COLUMN IF NOT EXISTS thesis TEXT;
ALTER TABLE tickers ADD COLUMN IF NOT EXISTS target_action VARCHAR;
ALTER TABLE tickers ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

UPDATE tickers
SET
  status = COALESCE(status, 'watching'),
  priority = COALESCE(priority, 'medium'),
  updated_at = COALESCE(updated_at, created_at, NOW());

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
