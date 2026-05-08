import { useState } from 'react';
import type { TickerData, WatchlistMetadata } from '../types/watchlist';
import type { MetricCatalogItem } from '../types/metrics';
import type { AiValuationResponse } from '../types/valuation';
import { AlertItem } from './AlertItem';
import { AiValuationPanel } from './AiValuationPanel';
import { InlineAlertForm } from './InlineAlertForm';
import { apiFetch } from '../lib/apiClient';
import { parseAiValuationResponse } from '../lib/valuation';

/**
 * Props for the TickerCard component.
 * @interface Props
 * @property {string} symbol - The stock ticker symbol.
 * @property {TickerData} data - The data containing alerts and company info for the ticker.
 * @property {Function} onDeleteTicker - Callback when the entire ticker is deleted.
 * @property {Function} onAddInline - Callback when a new metric alert is added inline.
 * @property {Function} onUpdateAlert - Callback when an alert's target value is updated.
 * @property {Function} onDeleteAlert - Callback when an alert is deleted.
 * @property {Function} onToggleAlert - Callback when an alert is toggled (active/inactive).
 */
interface Props {
  symbol: string;
  data: TickerData;
  metrics: MetricCatalogItem[];
  onDeleteTicker: (ticker: string) => void;
  onAddInline: (ticker: string, metric: string, operator: string, val: number, alertType?: string) => void;
  onUpdateAlert: (alertId: string, val: number) => void;
  onDeleteAlert: (alertId: string, ticker: string) => void;
  onToggleAlert: (alertId: string, isActive: boolean) => void;
  onAddTag: (ticker: string, name: string) => void;
  onRemoveTag: (ticker: string, tagNameOrId: string) => void;
  onUpdateMetadata: (ticker: string, metadata: Partial<WatchlistMetadata>) => void;
}

/**
 * TickerCard component renders a single stock's watchlist card.
 * It displays the company name, symbol, and a list of configured alerts.
 * Users can also add new alerts inline or delete the entire ticker.
 * 
 * @param {Props} props - The component props
 * @returns {JSX.Element} The rendered TickerCard component
 */
export function TickerCard({ symbol, data, metrics, onDeleteTicker, onAddInline, onUpdateAlert, onDeleteAlert, onToggleAlert, onAddTag, onRemoveTag, onUpdateMetadata }: Props) {
  const [addingMetric, setAddingMetric] = useState(false);
  const [addingTag, setAddingTag] = useState(false);
  const [newTag, setNewTag] = useState('');
  const [aiValuation, setAiValuation] = useState<AiValuationResponse | string | null>(null);
  const [loadingAi, setLoadingAi] = useState(false);

  const handleAddTag = () => {
    const tag = newTag.trim().toLowerCase();
    if (tag && !data.tags.some(existing => existing.name === tag)) {
      onAddTag(symbol, tag);
    }
    setNewTag('');
    setAddingTag(false);
  };

  const handleAiValuation = async () => {
    setLoadingAi(true);
    setAiValuation(null);
    try {
      const res = await apiFetch('/ai-valuation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticker: symbol })
      });
      if (res.ok) {
        const responseData = await res.json();
        setAiValuation(parseAiValuationResponse(responseData));
      } else {
        const err = await res.json();
        setAiValuation(`Error: ${err.detail || 'Failed to fetch valuation'}`);
      }
    } catch {
      setAiValuation('Network error');
    } finally {
      setLoadingAi(false);
    }
  };

  return (
    <div className="card">
      <div className="card-header">
        <div className="card-title-group">
          <h3>{symbol}</h3>
          <p className="company-name">{data.name}</p>
        </div>
        <button 
          type="button"
          className="btn-danger" 
          onClick={() => {
            if (window.confirm(`Are you sure you want to completely remove ${symbol} from the watchlist?`)) {
              onDeleteTicker(symbol);
            }
          }}
          title="Delete Ticker"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M3 6h18"></path>
            <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"></path>
            <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"></path>
            <line x1="10" y1="11" x2="10" y2="17"></line>
            <line x1="14" y1="11" x2="14" y2="17"></line>
          </svg>
        </button>
      </div>
      <div className="card-body">
        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.75rem', flexWrap: 'wrap' }}>
          <select
            value={data.status || 'watching'}
            onChange={e => onUpdateMetadata(symbol, { status: e.target.value })}
            style={{ padding: '4px 8px', fontSize: '0.78rem', borderRadius: '4px', background: 'var(--bg-color)', color: 'var(--text-color)', border: '1px solid var(--border-color)' }}
            aria-label={`${symbol} status`}
          >
            <option value="watching">Watching</option>
            <option value="researching">Researching</option>
            <option value="ready">Ready</option>
            <option value="holding">Holding</option>
            <option value="passed">Passed</option>
          </select>
          <select
            value={data.priority || 'medium'}
            onChange={e => onUpdateMetadata(symbol, { priority: e.target.value })}
            style={{ padding: '4px 8px', fontSize: '0.78rem', borderRadius: '4px', background: 'var(--bg-color)', color: 'var(--text-color)', border: '1px solid var(--border-color)' }}
            aria-label={`${symbol} priority`}
          >
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
          </select>
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '1rem', alignItems: 'center' }}>
          {data.tags.map(tag => (
            <span key={tag.id} style={{ background: tag.color || 'var(--primary)', color: 'white', padding: '2px 8px', borderRadius: '12px', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '4px' }}>
              #{tag.name}
              <button type="button" onClick={() => onRemoveTag(symbol, tag.id)} style={{ background: 'none', border: 'none', color: 'white', cursor: 'pointer', fontSize: '0.8rem', padding: 0, lineHeight: 1 }}>×</button>
            </span>
          ))}
          {addingTag ? (
            <input 
              type="text" 
              value={newTag} 
              onChange={e => setNewTag(e.target.value)}
              onKeyDown={e => { if(e.key === 'Enter') handleAddTag(); if(e.key === 'Escape') setAddingTag(false); }}
              autoFocus
              onBlur={handleAddTag}
              style={{ padding: '2px 6px', fontSize: '0.75rem', borderRadius: '4px', width: '80px', background: 'var(--bg-color)', color: 'var(--text-color)', border: '1px solid var(--border-color)' }}
              placeholder="Tag..."
            />
          ) : (
            <button type="button" onClick={() => setAddingTag(true)} style={{ background: 'transparent', border: '1px dashed var(--text-muted)', color: 'var(--text-muted)', padding: '2px 8px', borderRadius: '12px', fontSize: '0.75rem', cursor: 'pointer' }}>+ Tag</button>
          )}
        </div>
        
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <h4 style={{ margin: 0 }}>Configured Alerts:</h4>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button type="button" onClick={handleAiValuation} disabled={loadingAi} style={{ background: 'transparent', border: '1px solid var(--primary)', color: 'var(--primary)', cursor: 'pointer', borderRadius: '4px', padding: '2px 8px', fontSize: '0.8rem', fontWeight: 'bold' }}>
              {loadingAi ? '...' : 'AI Valuation'}
            </button>
            <button type="button" onClick={() => setAddingMetric(true)} style={{ background: 'transparent', border: '1px dashed var(--primary)', color: 'var(--primary)', cursor: 'pointer', borderRadius: '4px', padding: '2px 8px', fontSize: '0.8rem', fontWeight: 'bold' }}>+ Metric</button>
          </div>
        </div>

        {aiValuation && (
          <AiValuationPanel
            valuation={aiValuation}
            metrics={metrics}
            onClose={() => setAiValuation(null)}
          />
        )}

        {addingMetric && (
          <InlineAlertForm
            metrics={metrics}
            onSubmit={(selectedMetric, selectedOperator, targetValue, alertType) => {
              onAddInline(symbol, selectedMetric, selectedOperator, targetValue, alertType);
              setAddingMetric(false);
            }}
            onCancel={() => setAddingMetric(false)}
          />
        )}

        {data.alerts && data.alerts.length > 0 ? (
          <ul className="alerts-list">
            {data.alerts.map((alert) => (
              <AlertItem
                key={alert.id}
                symbol={symbol}
                alert={alert}
                onUpdate={onUpdateAlert}
                onDelete={onDeleteAlert}
                onToggle={onToggleAlert}
              />
            ))}
          </ul>
        ) : (
          <p className="no-alerts">No alerts</p>
        )}
      </div>
    </div>
  );
}
