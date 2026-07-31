import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { MetricSelect } from './MetricSelect';
import { TickerSearchInput } from './TickerSearchInput';
import { Icon } from './Icon';
import type { MetricCatalogItem } from '../types/metrics';

interface Props {
  metrics: MetricCatalogItem[];
  onAdd: (ticker: string, metric: string, operator: string, targetValue: number, alertType: string) => Promise<boolean>;
}

export function AlertForm({ metrics, onAdd }: Props) {
  const alertMetrics = useMemo(() => metrics.filter((item) => item.supported_for_alerts), [metrics]);
  const [ticker, setTicker] = useState('');
  const [metric, setMetric] = useState('pe');
  const [operator, setOperator] = useState('<');
  const [targetValue, setTargetValue] = useState('');
  const [alertType, setAlertType] = useState('absolute');
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    if (alertMetrics.length > 0 && !alertMetrics.some((item) => item.key === metric)) setMetric(alertMetrics[0].key);
  }, [alertMetrics, metric]);
  const selectedMetric = alertMetrics.find((item) => item.key === metric);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    const parsedTarget = Number.parseFloat(targetValue);
    if (!ticker.trim() || !Number.isFinite(parsedTarget)) return;
    setSubmitting(true);
    setFormError(null);
    try {
      const success = await onAdd(ticker.trim().toUpperCase(), metric, operator, parsedTarget, alertType);
      if (success) { setTicker(''); setTargetValue(''); }
      else setFormError('The alert could not be added. Check the ticker and try again.');
    } finally { setSubmitting(false); }
  };

  return (
    <section className="form-section alert-composer-section" aria-labelledby="create-alert-heading">
      <div className="section-heading compact"><div><h2 id="create-alert-heading">Create an alert</h2><p>Choose a company, a metric, and the threshold that should bring it back to your attention.</p></div></div>
      <form className="alert-form" onSubmit={handleSubmit}>
        <TickerSearchInput id="alert-ticker" label="Company ticker" value={ticker} onChange={setTicker} helpText="Use the exchange suffix for non-US listings." required />
        <div className="field field-wide">
          <label htmlFor="alert-metric">Metric</label>
          <MetricSelect metrics={metrics} value={metric} onChange={setMetric} support="alerts" disabled={submitting} />
          <span className="field-help">{selectedMetric?.description || 'Loading available metrics…'}</span>
        </div>
        <div className="field">
          <label htmlFor="alert-operator">Condition</label>
          <select id="alert-operator" value={operator} onChange={(event) => setOperator(event.target.value)}>
            <option value="<">Below (&lt;)</option><option value="<=">At or below (≤)</option><option value=">">Above (&gt;)</option><option value=">=">At or above (≥)</option><option value="==">Equal to (=)</option><option value="!=">Not equal to (≠)</option>
          </select>
        </div>
        <div className="field">
          <label htmlFor="alert-type">Threshold type</label>
          <select id="alert-type" value={alertType} onChange={(event) => setAlertType(event.target.value)}><option value="absolute">Metric value</option><option value="relative">Change from today</option></select>
          <span className="field-help">{alertType === 'relative' ? 'Enter the percentage change from the captured reference.' : 'Use the metric’s displayed unit.'}</span>
        </div>
        <div className="field">
          <label htmlFor="alert-target">{alertType === 'relative' ? 'Change target (%)' : 'Target value'}</label>
          <input id="alert-target" type="number" step="any" inputMode="decimal" placeholder={alertType === 'relative' ? '-20' : '16'} value={targetValue} onChange={(event) => setTargetValue(event.target.value)} required />
        </div>
        <div className="form-action"><button className="button button-primary" type="submit" disabled={submitting || alertMetrics.length === 0}><Icon name="plus" />{submitting ? 'Adding…' : 'Add alert'}</button></div>
      </form>
      {formError && <p className="form-error" role="alert">{formError}</p>}
    </section>
  );
}
