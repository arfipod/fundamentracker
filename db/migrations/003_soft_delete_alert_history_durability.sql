ALTER TABLE alerts ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS restored_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_alerts_deleted_at ON alerts(deleted_at);

ALTER TABLE alert_history ADD COLUMN IF NOT EXISTS ticker_symbol VARCHAR;
ALTER TABLE alert_history ADD COLUMN IF NOT EXISTS company_name VARCHAR;
ALTER TABLE alert_history ADD COLUMN IF NOT EXISTS metric VARCHAR;
ALTER TABLE alert_history ADD COLUMN IF NOT EXISTS operator VARCHAR;
ALTER TABLE alert_history ADD COLUMN IF NOT EXISTS alert_type VARCHAR;
ALTER TABLE alert_history ADD COLUMN IF NOT EXISTS reference_value NUMERIC;
ALTER TABLE alert_history ADD COLUMN IF NOT EXISTS current_value NUMERIC;
ALTER TABLE alert_history ADD COLUMN IF NOT EXISTS source VARCHAR;
ALTER TABLE alert_history ADD COLUMN IF NOT EXISTS as_of_date DATE;
ALTER TABLE alert_history ADD COLUMN IF NOT EXISTS fetched_at TIMESTAMPTZ;
ALTER TABLE alert_history ADD COLUMN IF NOT EXISTS message TEXT;

ALTER TABLE alert_history ALTER COLUMN alert_id DROP NOT NULL;

DO $$
DECLARE
  constraint_name TEXT;
BEGIN
  SELECT tc.constraint_name
  INTO constraint_name
  FROM information_schema.table_constraints tc
  JOIN information_schema.key_column_usage kcu
    ON tc.constraint_name = kcu.constraint_name
   AND tc.table_schema = kcu.table_schema
  WHERE tc.table_name = 'alert_history'
    AND tc.constraint_type = 'FOREIGN KEY'
    AND kcu.column_name = 'alert_id'
  LIMIT 1;

  IF constraint_name IS NOT NULL THEN
    EXECUTE format('ALTER TABLE alert_history DROP CONSTRAINT %I', constraint_name);
  END IF;
END $$;

ALTER TABLE alert_history
  ADD CONSTRAINT alert_history_alert_id_fkey
  FOREIGN KEY (alert_id) REFERENCES alerts(id) ON DELETE SET NULL;

UPDATE alert_history h
SET
  ticker_symbol = COALESCE(h.ticker_symbol, a.ticker_symbol),
  company_name = COALESCE(h.company_name, t.name),
  metric = COALESCE(h.metric, a.metric),
  operator = COALESCE(h.operator, a.operator),
  alert_type = COALESCE(h.alert_type, a.alert_type),
  reference_value = COALESCE(h.reference_value, a.reference_value),
  current_value = COALESCE(h.current_value, h.trigger_value)
FROM alerts a
LEFT JOIN tickers t ON t.symbol = a.ticker_symbol
WHERE h.alert_id = a.id;
