export interface DataQualityMetadata {
  source?: string | null;
  as_of_date?: string | null;
  fetched_at?: string | null;
  expires_at?: string | null;
  stale?: boolean | null;
  confidence?: number | null;
}

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
  current_source?: string | null;
  current_as_of_date?: string | null;
  current_fetched_at?: string | null;
  current_expires_at?: string | null;
  current_stale?: boolean | null;
  current_confidence?: number | null;
}

export interface WatchlistTag {
  id: string;
  name: string;
  color?: string | null;
}

export interface WatchlistMetadata {
  status: string;
  priority: string;
  notes?: string | null;
  thesis?: string | null;
  target_action?: string | null;
}

export interface TickerData {
  name: string;
  status: string;
  priority: string;
  notes?: string | null;
  thesis?: string | null;
  target_action?: string | null;
  tags: WatchlistTag[];
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
