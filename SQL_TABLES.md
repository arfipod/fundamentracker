Add this to supabase SQL to create tables
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
  reference_value NUMERIC, -- It will save the anchor price in dynamic alerts
  alert_type VARCHAR DEFAULT 'absolute', -- 'absolute' o 'relative'
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
-- Insert the default scan settings
INSERT INTO scan_settings (id, interval_seconds, last_scan_time) VALUES (1, 0, 0);
```