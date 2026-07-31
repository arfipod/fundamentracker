export interface MetricCatalogItem {
  key: string;
  yf_key: string | null;
  unit: string;
  multiplier: number;
  category: string;
  label: string;
  description: string;
  higher_is_better: boolean | null;
  supported_for_alerts: boolean;
  supported_for_history: boolean;
  source_kind?: string;
  period?: string | null;
  formula?: string | null;
}

export function getMetricLabel(metrics: MetricCatalogItem[], key: string): string {
  return metrics.find(metric => metric.key === key)?.label ?? key.toUpperCase();
}

export function formatMetricValue(
  metrics: MetricCatalogItem[],
  key: string,
  value: number | null | undefined
): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return 'N/A';

  const definition = metrics.find(metric => metric.key === key);
  const maximumFractionDigits = definition?.unit === 'currency' ? 2 : 4;
  const formatted = value.toLocaleString(undefined, { maximumFractionDigits });

  if (definition?.unit === 'percent') return `${formatted}%`;
  if (definition?.unit === 'percentage_points') return `${formatted} pp`;
  if (definition?.unit === 'ratio') return `${formatted}×`;
  if (definition?.unit === 'count') return Math.round(value).toLocaleString();
  return formatted;
}
