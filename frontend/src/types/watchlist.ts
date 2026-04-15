export interface Alert {
  metric: string;
  operator: string;
  target: number;
  is_triggered?: boolean;
  current_value?: number | null;
}

export interface TickerData {
  name: string;
  alerts: Alert[];
}

export interface Watchlist {
  [key: string]: TickerData;
}
