import { useState } from 'react';
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

export function TickerCard({ symbol, data, onDeleteTicker, onAddInline, onUpdateAlert, onDeleteAlert, onToggleAlert }: Props) {
  const [addingMetric, setAddingMetric] = useState(false);

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
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <h4 style={{ margin: 0 }}>Configured Alerts:</h4>
          <button type="button" onClick={() => setAddingMetric(true)} style={{ background: 'transparent', border: '1px dashed var(--primary)', color: 'var(--primary)', cursor: 'pointer', borderRadius: '4px', padding: '2px 8px', fontSize: '0.8rem', fontWeight: 'bold' }}>+ Metric</button>
        </div>

        {addingMetric && (
          <div style={{ padding: '0.5rem', background: 'var(--bg-color)', borderRadius: '6px', marginBottom: '0.5rem', display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
            <select id={`inline-m-${symbol}`} className="target-edit-input" style={{ width: 'auto', padding: '2px 4px' }}>
              <option value="pe">PE</option>
              <option value="fpe">FPE</option>
              <option value="pb">PB</option>
              <option value="evebitda">EV/EBITDA</option>
              <option value="roe">ROE</option>
              <option value="price">Price</option>
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
