export interface MetricCatalogItem {
  key: string;
  yf_key: string;
  unit: string;
  multiplier: number;
  category: string;
  label: string;
  description: string;
  higher_is_better: boolean | null;
  supported_for_alerts: boolean;
  supported_for_history: boolean;
}

export function getMetricLabel(metrics: MetricCatalogItem[], key: string): string {
  return metrics.find(metric => metric.key === key)?.label ?? key.toUpperCase();
}
