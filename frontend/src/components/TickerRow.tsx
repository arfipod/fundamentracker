import { useState, useEffect } from 'react';
import type { TickerData } from '../types/watchlist';
import { AlertItem } from './AlertItem';

interface Props {
  symbol: string;
  data: TickerData;
  onDeleteTicker: (ticker: string) => void;
  onAddInline: (ticker: string, metric: string, operator: string, val: number) => void;
  onUpdateAlert: (ticker: string, metric: string, val: number) => void;
  onDeleteAlert: (ticker: string, metric: string) => void;
  onToggleAlert: (alertId: string, isActive: boolean) => void;
}

export function TickerRow({ symbol, data, onDeleteTicker, onAddInline, onUpdateAlert, onDeleteAlert, onToggleAlert }: Props) {
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
    <>
      <tr className="ticker-row">
        <td style={{ fontWeight: 'bold', color: 'var(--text-main)' }}>{symbol}</td>
        <td style={{ color: '#64748b', fontSize: '0.9rem' }}>
          <div style={{ marginBottom: '0.5rem' }}>{data.name}</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
            {tags.map(tag => (
              <span key={tag} style={{ background: 'var(--primary)', color: 'white', padding: '1px 6px', borderRadius: '8px', fontSize: '0.7rem', display: 'flex', alignItems: 'center', gap: '2px' }}>
                #{tag}
                <button onClick={() => handleRemoveTag(tag)} style={{ background: 'none', border: 'none', color: 'white', cursor: 'pointer', fontSize: '0.75rem', padding: 0, lineHeight: 1 }}>×</button>
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
                style={{ padding: '1px 4px', fontSize: '0.7rem', borderRadius: '4px', width: '60px', background: 'var(--bg-color)', color: 'var(--text-color)', border: '1px solid var(--border-color)' }}
                placeholder="Tag..."
              />
            ) : (
              <button onClick={() => setAddingTag(true)} style={{ background: 'transparent', border: '1px dashed var(--text-muted)', color: 'var(--text-muted)', padding: '1px 6px', borderRadius: '8px', fontSize: '0.7rem', cursor: 'pointer' }}>+ Tag</button>
            )}
          </div>
        </td>
        <td>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {data.alerts && data.alerts.length > 0 ? (
              <div className="alerts-list" style={{ gap: '0.3rem' }}>
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
              </div>
            ) : (
              <span style={{ fontSize: '0.85rem', color: '#64748b', fontStyle: 'italic' }}>No alerts</span>
            )}

            {addingMetric ? (
              <div style={{ padding: '0.5rem', background: 'var(--bg-color)', borderRadius: '6px', display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap', marginTop: '0.5rem' }}>
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
                <input type="number" step="any" placeholder="Val" id={`inline-t-${symbol}`} className="target-edit-input" style={{ width: '60px', padding: '2px 4px' }} onKeyDown={(e) => { if (e.key === 'Enter') handleAddSubmit(); if (e.key === 'Escape') setAddingMetric(false); }} />
                <div style={{ display: 'flex', gap: '4px' }}>
                  <button className="btn-success" style={{ padding: '2px 6px', fontSize: '0.8rem' }} onClick={handleAddSubmit}>✓</button>
                  <button className="btn-danger" style={{ padding: '2px 6px', fontSize: '0.8rem' }} onClick={() => setAddingMetric(false)}>✕</button>
                </div>
              </div>
            ) : (
              <button type="button" onClick={() => setAddingMetric(true)} style={{ background: 'transparent', border: '1px dashed var(--primary)', color: 'var(--primary)', cursor: 'pointer', borderRadius: '4px', padding: '2px 8px', fontSize: '0.8rem', fontWeight: 'bold', alignSelf: 'flex-start', marginTop: '0.5rem' }}>+ Metric</button>
            )}
          </div>
        </td>
        <td style={{ textAlign: 'right' }}>
          <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
            <button 
              type="button"
              className="btn-primary" 
              onClick={handleAiValuation}
              disabled={loadingAi}
              title="AI Valuation"
              style={{ padding: '4px 8px', fontSize: '0.75rem', fontWeight: 'bold' }}
            >
              {loadingAi ? '...' : 'AI'}
            </button>
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
        </td>
      </tr>
      {aiValuation && (
        <tr className="ai-valuation-row">
          <td colSpan={4}>
            <div style={{ padding: '0.75rem', background: 'rgba(59, 130, 246, 0.1)', border: '1px solid var(--primary)', borderRadius: '6px', margin: '0 1rem 1rem 1rem', fontSize: '0.85rem', position: 'relative' }}>
              <button onClick={() => setAiValuation(null)} style={{ position: 'absolute', top: '4px', right: '4px', background: 'none', border: 'none', color: 'var(--text-color)', cursor: 'pointer' }}>✕</button>
              <h5 style={{ margin: '0 0 0.5rem 0', color: 'var(--primary)' }}>✨ Gemini AI Analysis</h5>
              <p style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{aiValuation}</p>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}
