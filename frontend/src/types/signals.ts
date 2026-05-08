export interface Signal {
  id: string;
  ticker_symbol?: string | null;
  company_name?: string | null;
  signal_type: string;
  severity?: string | null;
  title: string;
  message?: string | null;
  metric?: string | null;
  current_value?: number | null;
  previous_value?: number | null;
  target_value?: number | null;
  source?: string | null;
  as_of_date?: string | null;
  fetched_at?: string | null;
  created_at: string;
  acknowledged_at?: string | null;
  dismissed_at?: string | null;
  raw_payload?: Record<string, unknown> | null;
}
