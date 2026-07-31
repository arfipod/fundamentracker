import { useState, type FormEvent } from 'react';
import type { Alert } from '../types/watchlist';
import { formatMetricValue, getMetricLabel, type MetricCatalogItem } from '../types/metrics';
import { DataQualityBadge } from './DataQualityBadge';
import { MetricChart } from './MetricChart';
import { Icon } from './Icon';

interface Props {
  symbol: string; alert: Alert; metrics: MetricCatalogItem[];
  onUpdate: (alertId: string, val: number) => void;
  onDelete: (alertId: string, ticker: string) => void;
  onToggle?: (alertId: string, isActive: boolean) => void;
}

export function AlertItem({ symbol, alert, metrics, onUpdate, onDelete, onToggle }: Props) {
  const [isEditing, setIsEditing] = useState(false);
  const [editingValue, setEditingValue] = useState(alert.target.toString());
  const [showChart, setShowChart] = useState(false);
  const isRelative = alert.alert_type === 'relative';
  const metricDefinition = metrics.find((metric) => metric.key === alert.metric);
  const canShowChart = Boolean(metricDefinition?.supported_for_history);
  const relativeDiff = isRelative && alert.current_value !== undefined && alert.current_value !== null && alert.reference_value !== undefined && alert.reference_value !== null && alert.reference_value !== 0 ? ((alert.current_value / alert.reference_value) - 1) * 100 : null;
  const conditionValue = isRelative ? relativeDiff : alert.current_value;
  const conditionMet = (() => {
    if (conditionValue === undefined || conditionValue === null) return null;
    switch (alert.operator) { case '<': return conditionValue < alert.target; case '<=': return conditionValue <= alert.target; case '>': return conditionValue > alert.target; case '>=': return conditionValue >= alert.target; case '==': return conditionValue === alert.target; case '!=': return conditionValue !== alert.target; default: return null; }
  })();
  const conditionClass = conditionMet === true ? 'met' : conditionMet === false ? 'not-met' : 'unknown';
  const targetLabel = isRelative ? `${alert.target.toLocaleString()}%` : formatMetricValue(metrics, alert.metric, alert.target);
  const currentLabel = formatMetricValue(metrics, alert.metric, alert.current_value);
  const qualityMetadata = { source: alert.current_source, as_of_date: alert.current_as_of_date, fetched_at: alert.current_fetched_at, expires_at: alert.current_expires_at, stale: alert.current_stale, confidence: alert.current_confidence };
  const hasQualityMetadata = Object.values(qualityMetadata).some((value) => value !== undefined && value !== null && value !== '');
  const handleSave = (event: FormEvent) => { event.preventDefault(); const value = Number.parseFloat(editingValue); if (Number.isFinite(value)) onUpdate(alert.id, value); setIsEditing(false); };
  const removeAlert = () => { if (window.confirm(`Delete the ${getMetricLabel(metrics, alert.metric)} alert for ${symbol}?`)) onDelete(alert.id, symbol); };

  return (
    <li className={`alert-item ${conditionClass}${alert.is_active ? '' : ' inactive'}${alert.is_triggered ? ' triggered' : ''}`}>
      <div className="alert-row-main">
        <div className="alert-state" title={alert.is_active ? 'Alert active' : 'Alert paused'}><span className="alert-state-dot" aria-hidden="true" /><span className="visually-hidden">{alert.is_active ? 'Active alert' : 'Paused alert'}</span></div>
        <div className="alert-rule"><strong>{getMetricLabel(metrics, alert.metric)}</strong><div className="alert-expression"><span>{alert.operator}</span>{isEditing ? <form className="alert-edit-form" onSubmit={handleSave}><label className="visually-hidden" htmlFor={`target-${alert.id}`}>New target value</label><input id={`target-${alert.id}`} type="number" step="any" inputMode="decimal" autoFocus value={editingValue} onChange={(event) => setEditingValue(event.target.value)} onKeyDown={(event) => { if (event.key === 'Escape') { setEditingValue(alert.target.toString()); setIsEditing(false); } }} /><button className="icon-button icon-button-small" type="submit" aria-label="Save target" title="Save target"><Icon name="check" size={15} /></button><button className="icon-button icon-button-small" type="button" aria-label="Cancel editing" title="Cancel" onClick={() => setIsEditing(false)}><Icon name="close" size={15} /></button></form> : <button className="alert-target-button" type="button" onClick={() => { setEditingValue(alert.target.toString()); setIsEditing(true); }} title="Edit target">{targetLabel}</button>}</div></div>
        <div className="alert-observation"><span className="alert-current-label">Current</span><strong>{currentLabel}</strong><span className={`condition-label ${conditionClass}`}>{conditionMet === true ? 'Condition met' : conditionMet === false ? 'Not met' : 'Waiting for data'}</span></div>
        <div className="alert-provenance">{isRelative && alert.reference_value !== undefined && alert.reference_value !== null && <span>Reference {formatMetricValue(metrics, alert.metric, alert.reference_value)}</span>}{relativeDiff !== null && <span>Change {relativeDiff >= 0 ? '+' : ''}{relativeDiff.toFixed(2)}%</span>}{hasQualityMetadata && <DataQualityBadge metadata={qualityMetadata} />}</div>
        <div className="alert-actions">
          {canShowChart && <button className="icon-button" type="button" aria-label={`${showChart ? 'Hide' : 'Show'} ${getMetricLabel(metrics, alert.metric)} history`} title={showChart ? 'Hide history' : 'Show history'} aria-pressed={showChart} onClick={() => setShowChart((current) => !current)}><Icon name="chart" /></button>}
          {onToggle && <button className="icon-button" type="button" aria-label={alert.is_active ? 'Pause alert' : 'Activate alert'} title={alert.is_active ? 'Pause alert' : 'Activate alert'} onClick={() => onToggle(alert.id, !alert.is_active)}><Icon name={alert.is_active ? 'pause' : 'play'} /></button>}
          <button className="icon-button danger-text" type="button" aria-label="Delete alert" title="Delete alert" onClick={removeAlert}><Icon name="trash" /></button>
        </div>
      </div>
      {showChart && canShowChart && <div className="alert-chart"><MetricChart ticker={symbol} metric={alert.metric} currentValue={alert.current_value} targetValue={isRelative ? null : alert.target} height={260} showPeriodToggle showReferenceLineToggle /></div>}
    </li>
  );
}
