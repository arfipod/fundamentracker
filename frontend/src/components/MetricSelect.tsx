import type { CSSProperties } from 'react';
import type { MetricCatalogItem } from '../types/metrics';

type MetricSupport = 'alerts' | 'history' | 'all';
interface MetricSelectProps { id?: string; metrics: MetricCatalogItem[]; value: string; onChange: (metric: string) => void; support?: MetricSupport; className?: string; style?: CSSProperties; disabled?: boolean; }
function supportsMetric(metric: MetricCatalogItem, support: MetricSupport): boolean { if (support === 'alerts') return metric.supported_for_alerts; if (support === 'history') return metric.supported_for_history; return true; }
export function MetricSelect({ id, metrics, value, onChange, support = 'all', className, style, disabled = false }: MetricSelectProps) {
  const availableMetrics = metrics.filter((metric) => supportsMetric(metric, support));
  const groupedMetrics = availableMetrics.reduce<Record<string, MetricCatalogItem[]>>((groups, metric) => { const category = metric.category || 'Other'; groups[category] = groups[category] || []; groups[category].push(metric); return groups; }, {});
  return <select id={id} value={value} onChange={(event) => onChange(event.target.value)} className={className} style={style} disabled={disabled || availableMetrics.length === 0}>{availableMetrics.length === 0 ? <option value={value}>Loading metrics…</option> : Object.entries(groupedMetrics).map(([category, categoryMetrics]) => <optgroup key={category} label={category}>{categoryMetrics.map((metric) => <option key={metric.key} value={metric.key}>{metric.label}</option>)}</optgroup>)}</select>;
}
