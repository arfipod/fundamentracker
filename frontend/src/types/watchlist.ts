export interface Alert {
  id: string;
  metric: string;
  operator: string;
  target: number;
  is_active: boolean;
  is_triggered: boolean;
  reference_value?: number | null;
  alert_type?: string;
  current_value?: number | null;
}

export interface TickerData {
  name: string;
  alerts: Alert[];
}

export interface Watchlist {
  [key: string]: TickerData;
}

export interface AlertHistoryEntry {
  id: string;
  alert_id: string;
  triggered_at: string;
  trigger_value: number;
  target_value: number;
  ticker_symbol?: string | null;
  company_name?: string | null;
  metric?: string | null;
  operator?: string | null;
  alert_type?: string | null;
  reference_value?: number | null;
  current_value?: number | null;
  source?: string | null;
  as_of_date?: string | null;
  fetched_at?: string | null;
  message?: string | null;
  alerts?: {
    ticker_symbol: string;
    metric: string;
  };
}
