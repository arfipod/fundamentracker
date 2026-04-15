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
  alerts?: {
    ticker_symbol: string;
    metric: string;
  };
}
