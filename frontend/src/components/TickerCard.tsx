import { useState, useEffect } from 'react';
import type { TickerData } from '../types/watchlist';
import { AlertItem } from './AlertItem';

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
  onDeleteTicker: (ticker: string) => void;
  onAddInline: (ticker: string, metric: string, operator: string, val: number) => void;
  onUpdateAlert: (ticker: string, metric: string, val: number) => void;
  onDeleteAlert: (ticker: string, metric: string) => void;
  onToggleAlert: (alertId: string, isActive: boolean) => void;
}

/**
 * TickerCard component renders a single stock's watchlist card.
 * It displays the company name, symbol, and a list of configured alerts.
 * Users can also add new alerts inline or delete the entire ticker.
 * 
 * @param {Props} props - The component props
 * @returns {JSX.Element} The rendered TickerCard component
 */
export function TickerCard({ symbol, data, onDeleteTicker, onAddInline, onUpdateAlert, onDeleteAlert, onToggleAlert }: Props) {
  const [addingMetric, setAddingMetric] = useState(false);
  const [tags, setTags] = useState<string[]>([]);
  const [addingTag, setAddingTag] = useState(false);
  const [newTag, setNewTag] = useState('');
  const [aiValuation, setAiValuation] = useState<string | null>(null);
  const [loadingAi, setLoadingAi] = useState(false);

  useEffect(() => {
    const savedTags = localStorage.getItem(`tags_${symbol}`);
    if (savedTags) {
      setTags(JSON.parse(savedTags));
    }
  }, [symbol]);

  const saveTags = (newTags: string[]) => {
    setTags(newTags);
    localStorage.setItem(`tags_${symbol}`, JSON.stringify(newTags));
    window.dispatchEvent(new Event('tagsUpdated'));
  };

  const handleAddTag = () => {
    if (newTag.trim() && !tags.includes(newTag.trim().toLowerCase())) {
      saveTags([...tags, newTag.trim().toLowerCase()]);
    }
    setNewTag('');
    setAddingTag(false);
  };

  const handleRemoveTag = (tag: string) => {
    saveTags(tags.filter(t => t !== tag));
  };

  const handleAiValuation = async () => {
    setLoadingAi(true);
    setAiValuation(null);
    try {
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const res = await fetch(`${API_URL}/ai-valuation`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticker: symbol })
      });
      if (res.ok) {
        const data = await res.json();
        setAiValuation(data.analysis);
      } else {
        const err = await res.json();
        setAiValuation(`Error: ${err.detail || 'Failed to fetch valuation'}`);
      }
    } catch (e) {
      setAiValuation('Network error');
    } finally {
      setLoadingAi(false);
    }
  };

  const handleAddSubmit = () => {
    const mElement = document.getElementById(`inline-m-${symbol}`) as HTMLSelectElement;
    const oElement = document.getElementById(`inline-o-${symbol}`) as HTMLSelectElement;
    const tElement = document.getElementById(`inline-t-${symbol}`) as HTMLInputElement;

    if (tElement && tElement.value) {
      onAddInline(symbol, mElement.value, oElement.value, parseFloat(tElement.value));
      setAddingMetric(false);
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
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '1rem', alignItems: 'center' }}>
          {tags.map(tag => (
            <span key={tag} style={{ background: 'var(--primary)', color: 'white', padding: '2px 8px', borderRadius: '12px', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '4px' }}>
              #{tag}
              <button onClick={() => handleRemoveTag(tag)} style={{ background: 'none', border: 'none', color: 'white', cursor: 'pointer', fontSize: '0.8rem', padding: 0, lineHeight: 1 }}>×</button>
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
            <button onClick={() => setAddingTag(true)} style={{ background: 'transparent', border: '1px dashed var(--text-muted)', color: 'var(--text-muted)', padding: '2px 8px', borderRadius: '12px', fontSize: '0.75rem', cursor: 'pointer' }}>+ Tag</button>
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
          <div style={{ padding: '0.75rem', background: 'rgba(59, 130, 246, 0.1)', border: '1px solid var(--primary)', borderRadius: '6px', marginBottom: '1rem', fontSize: '0.85rem', position: 'relative' }}>
            <button onClick={() => setAiValuation(null)} style={{ position: 'absolute', top: '4px', right: '4px', background: 'none', border: 'none', color: 'var(--text-color)', cursor: 'pointer' }}>✕</button>
            <h5 style={{ margin: '0 0 0.5rem 0', color: 'var(--primary)' }}>✨ Gemini AI Analysis</h5>
            <p style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{aiValuation}</p>
          </div>
        )}

        {addingMetric && (
          <div style={{ padding: '0.5rem', background: 'var(--bg-color)', borderRadius: '6px', marginBottom: '0.5rem', display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
            <select id={`inline-m-${symbol}`} className="target-edit-input" style={{ width: 'auto', padding: '2px 4px' }}>
              <option value="pe">PE</option>
              <option value="fpe">FPE</option>
              <option value="pb">PB</option>
              <option value="evebitda">EV/EBITDA</option>
              <option value="roe">ROE</option>
              <option value="price">Price</option>
              <option value="roic">ROIC</option>
              <option value="dividendyield">Dividend Yield</option>
              <option value="payoutratio">Payout Ratio</option>
              <option value="debttoequity">Debt to Equity</option>
              <option value="profitmargins">Profit Margins</option>
              <option value="operatingmargins">Operating Margins</option>
            </select>
            <select id={`inline-o-${symbol}`} className="target-edit-input" style={{ width: 'auto', padding: '2px 4px' }}>
              <option value="<">&lt;</option>
              <option value=">">&gt;</option>
              <option value="<=">&lt;=</option>
              <option value=">=">&gt;=</option>
              <option value="==">==</option>
              <option value="!=">!=</option>
            </select>
            <input type="number" step="any" placeholder="Valor" id={`inline-t-${symbol}`} className="target-edit-input" style={{ width: '60px', padding: '2px 4px' }} onKeyDown={(e) => { if (e.key === 'Enter') handleAddSubmit(); if (e.key === 'Escape') setAddingMetric(false); }} />
            <div style={{ display: 'flex', gap: '4px' }}>
              <button className="btn-success" style={{ padding: '2px 6px', fontSize: '0.8rem' }} onClick={handleAddSubmit}>✓</button>
              <button className="btn-danger" style={{ padding: '2px 6px', fontSize: '0.8rem' }} onClick={() => setAddingMetric(false)}>✕</button>
            </div>
          </div>
        )}

        {data.alerts && data.alerts.length > 0 ? (
          <ul className="alerts-list">
            {data.alerts.map((alert, idx) => (
              <AlertItem
                key={`${alert.metric}-${idx}`}
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
