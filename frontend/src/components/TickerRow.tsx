import { useState } from 'react';
import type { TickerData, WatchlistMetadata } from '../types/watchlist';
import type { MetricCatalogItem } from '../types/metrics';
import type { AiValuationResponse } from '../types/valuation';
import { AlertItem } from './AlertItem';
import { AiValuationPanel } from './AiValuationPanel';
import { InlineAlertForm } from './InlineAlertForm';
import { AuditedSecFactsPanel } from './AuditedSecFactsPanel';
import { TickerMetaControls } from './TickerMetaControls';
import { Icon } from './Icon';
import { apiFetch } from '../lib/apiClient';
import { parseAiValuationResponse } from '../lib/valuation';
import { useSecFacts } from '../hooks/useSecFacts';

interface Props {
  symbol: string; data: TickerData; metrics: MetricCatalogItem[];
  onDeleteTicker: (ticker: string) => void;
  onAddInline: (ticker: string, metric: string, operator: string, val: number, alertType?: string) => void;
  onUpdateAlert: (alertId: string, val: number) => void;
  onDeleteAlert: (alertId: string, ticker: string) => void;
  onToggleAlert: (alertId: string, isActive: boolean) => void;
  onAddTag: (ticker: string, name: string) => void;
  onRemoveTag: (ticker: string, tagNameOrId: string) => void;
  onUpdateMetadata: (ticker: string, metadata: Partial<WatchlistMetadata>) => void;
}

export function TickerRow({ symbol, data, metrics, onDeleteTicker, onAddInline, onUpdateAlert, onDeleteAlert, onToggleAlert, onAddTag, onRemoveTag, onUpdateMetadata }: Props) {
  const [addingMetric, setAddingMetric] = useState(false);
  const [aiValuation, setAiValuation] = useState<AiValuationResponse | string | null>(null);
  const [loadingAi, setLoadingAi] = useState(false);
  const [showSecFacts, setShowSecFacts] = useState(false);
  const secFacts = useSecFacts(symbol);

  const handleSecFacts = () => { const nextVisible = !showSecFacts; setShowSecFacts(nextVisible); if (nextVisible) secFacts.load(); };
  const handleResearchBrief = async () => {
    setLoadingAi(true); setAiValuation(null);
    try {
      const response = await apiFetch('/ai-valuation', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ticker: symbol }) });
      if (response.ok) setAiValuation(parseAiValuationResponse(await response.json()));
      else { const body = await response.json(); setAiValuation(`Error: ${body.detail || 'The research brief could not be generated.'}`); }
    } catch { setAiValuation('The research brief could not be generated because the API is unavailable.'); }
    finally { setLoadingAi(false); }
  };
  const removeTicker = () => { if (window.confirm(`Remove ${symbol} and all of its alerts from the watchlist?`)) onDeleteTicker(symbol); };

  return (
    <>
      <tr className="ticker-row">
        <td className="ticker-symbol-cell"><strong>{symbol}</strong><span>{data.alerts.length} alert{data.alerts.length === 1 ? '' : 's'}</span></td>
        <td className="ticker-company-cell"><div className="company-name">{data.name}</div><TickerMetaControls symbol={symbol} data={data} compact onAddTag={onAddTag} onRemoveTag={onRemoveTag} onUpdateMetadata={onUpdateMetadata} /></td>
        <td className="ticker-alerts-cell">
          {data.alerts.length > 0 ? <ul className="alerts-list compact-alerts">{data.alerts.map((alert) => <AlertItem key={alert.id} symbol={symbol} alert={alert} metrics={metrics} onUpdate={onUpdateAlert} onDelete={onDeleteAlert} onToggle={onToggleAlert} />)}</ul> : <p className="inline-empty">No alert rules yet.</p>}
          {addingMetric ? <InlineAlertForm metrics={metrics} onSubmit={(selectedMetric, selectedOperator, targetValue, alertType) => { onAddInline(symbol, selectedMetric, selectedOperator, targetValue, alertType); setAddingMetric(false); }} onCancel={() => setAddingMetric(false)} /> : <button className="text-button" type="button" onClick={() => setAddingMetric(true)}><Icon name="plus" size={15} />Add alert</button>}
        </td>
        <td className="ticker-actions-cell"><div className="ticker-row-actions">
          <button className="button button-quiet button-small" type="button" onClick={handleResearchBrief} disabled={loadingAi}><Icon name="sparkles" />{loadingAi ? 'Working…' : 'Research'}</button>
          <button className="button button-quiet button-small" type="button" onClick={handleSecFacts} disabled={secFacts.loading} aria-pressed={showSecFacts}><Icon name="database" />SEC</button>
          <button className="icon-button danger-text" type="button" onClick={removeTicker} aria-label={`Remove ${symbol} from watchlist`} title={`Remove ${symbol}`}><Icon name="trash" /></button>
        </div></td>
      </tr>
      {showSecFacts && <tr className="expanded-row"><td colSpan={4}><AuditedSecFactsPanel data={secFacts.data} loading={secFacts.loading} error={secFacts.error} /></td></tr>}
      {aiValuation && <tr className="expanded-row"><td colSpan={4}><AiValuationPanel valuation={aiValuation} metrics={metrics} onClose={() => setAiValuation(null)} /></td></tr>}
    </>
  );
}
