import { useEffect, useId, useMemo, useState, type FormEvent } from 'react';
import { MetricSelect } from './MetricSelect';
import { Icon } from './Icon';
import type { MetricCatalogItem } from '../types/metrics';

interface InlineAlertFormProps { metrics: MetricCatalogItem[]; onSubmit: (metric: string, operator: string, targetValue: number, alertType: string) => void; onCancel: () => void; }
export function InlineAlertForm({ metrics, onSubmit, onCancel }: InlineAlertFormProps) {
  const formId = useId();
  const alertMetrics = useMemo(() => metrics.filter((metric) => metric.supported_for_alerts), [metrics]);
  const [metric, setMetric] = useState('pe'); const [operator, setOperator] = useState('<'); const [alertType, setAlertType] = useState('absolute'); const [targetValue, setTargetValue] = useState('');
  useEffect(() => { if (alertMetrics.length > 0 && !alertMetrics.some((item) => item.key === metric)) setMetric(alertMetrics[0].key); }, [alertMetrics, metric]);
  const handleSubmit = (event: FormEvent) => { event.preventDefault(); const parsedTarget = Number.parseFloat(targetValue); if (!Number.isFinite(parsedTarget)) return; onSubmit(metric, operator, parsedTarget, alertType); setTargetValue(''); };
  return (
    <form className="inline-alert-form" onSubmit={handleSubmit}>
      <div className="field"><label htmlFor={`${formId}-metric`}>Metric</label><MetricSelect id={`${formId}-metric`} metrics={metrics} value={metric} onChange={setMetric} support="alerts" /></div>
      <div className="field"><label htmlFor={`${formId}-operator`}>Condition</label><select id={`${formId}-operator`} value={operator} onChange={(event) => setOperator(event.target.value)}><option value="<">Below</option><option value="<=">At or below</option><option value=">">Above</option><option value=">=">At or above</option><option value="==">Equal to</option><option value="!=">Not equal to</option></select></div>
      <div className="field"><label htmlFor={`${formId}-type`}>Type</label><select id={`${formId}-type`} value={alertType} onChange={(event) => setAlertType(event.target.value)}><option value="absolute">Metric value</option><option value="relative">Change from today</option></select></div>
      <div className="field"><label htmlFor={`${formId}-target`}>Target</label><input id={`${formId}-target`} type="number" step="any" inputMode="decimal" placeholder={alertType === 'relative' ? '-20' : '16'} value={targetValue} onChange={(event) => setTargetValue(event.target.value)} onKeyDown={(event) => { if (event.key === 'Escape') onCancel(); }} required /></div>
      <div className="inline-form-actions"><button className="button button-primary button-small" type="submit" disabled={alertMetrics.length === 0}><Icon name="plus" />Add alert</button><button className="button button-quiet button-small" type="button" onClick={onCancel}>Cancel</button></div>
    </form>
  );
}
