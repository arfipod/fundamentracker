import { useEffect, useMemo, useState } from 'react';
import { MetricSelect } from './MetricSelect';
import type { MetricCatalogItem } from '../types/metrics';

interface InlineAlertFormProps {
  metrics: MetricCatalogItem[];
  onSubmit: (metric: string, operator: string, targetValue: number, alertType: string) => void;
  onCancel: () => void;
}

export function InlineAlertForm({ metrics, onSubmit, onCancel }: InlineAlertFormProps) {
  const alertMetrics = useMemo(
    () => metrics.filter(metric => metric.supported_for_alerts),
    [metrics]
  );
  const [metric, setMetric] = useState('pe');
  const [operator, setOperator] = useState('<');
  const [alertType, setAlertType] = useState('absolute');
  const [targetValue, setTargetValue] = useState('');

  useEffect(() => {
    if (alertMetrics.length > 0 && !alertMetrics.some(item => item.key === metric)) {
      setMetric(alertMetrics[0].key);
    }
  }, [alertMetrics, metric]);

  const handleSubmit = () => {
    if (!targetValue) return;

    onSubmit(metric, operator, parseFloat(targetValue), alertType);
    setTargetValue('');
  };

  return (
    <div style={{ padding: '0.5rem', background: 'var(--bg-color)', borderRadius: '6px', display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap', marginTop: '0.5rem' }}>
      <MetricSelect
        metrics={metrics}
        value={metric}
        onChange={setMetric}
        support="alerts"
        className="target-edit-input"
        style={{ width: 'auto', padding: '2px 4px' }}
      />
      <select value={operator} onChange={event => setOperator(event.target.value)} className="target-edit-input" style={{ width: 'auto', padding: '2px 4px' }}>
        <option value="<">&lt;</option>
        <option value=">">&gt;</option>
        <option value="<=">&lt;=</option>
        <option value=">=">&gt;=</option>
        <option value="==">==</option>
        <option value="!=">!=</option>
      </select>
      <select value={alertType} onChange={event => setAlertType(event.target.value)} className="target-edit-input" style={{ width: 'auto', padding: '2px 4px' }}>
        <option value="absolute">Value</option>
        <option value="relative">Change %</option>
      </select>
      <input
        type="number"
        step="any"
        placeholder="Val"
        value={targetValue}
        onChange={event => setTargetValue(event.target.value)}
        className="target-edit-input"
        style={{ width: '60px', padding: '2px 4px' }}
        onKeyDown={event => {
          if (event.key === 'Enter') handleSubmit();
          if (event.key === 'Escape') onCancel();
        }}
      />
      <div style={{ display: 'flex', gap: '4px' }}>
        <button className="btn-success" style={{ padding: '2px 6px', fontSize: '0.8rem' }} onClick={handleSubmit}>Add</button>
        <button className="btn-danger" style={{ padding: '2px 6px', fontSize: '0.8rem' }} onClick={onCancel}>Cancel</button>
      </div>
    </div>
  );
}
