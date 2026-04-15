import { useState } from 'react';
import type { Alert } from '../types/watchlist';

interface Props {
  symbol: string;
  alert: Alert;
  onUpdate: (ticker: string, metric: string, val: number) => void;
  onDelete: (ticker: string, metric: string) => void;
  onToggle?: (alertId: string, isActive: boolean) => void;
}

export function AlertItem({ symbol, alert, onUpdate, onDelete, onToggle }: Props) {
  const [isEditing, setIsEditing] = useState(false);
  const [editingValue, setEditingValue] = useState(alert.target.toString());

  const handleSave = () => {
    const val = parseFloat(parseFloat(editingValue).toFixed(2));
    if (!isNaN(val)) {
      onUpdate(symbol, alert.metric, val);
    }
    setIsEditing(false);
  };

  const isRelative = alert.alert_type === 'relative';
  
  return (
    <li style={{ position: 'relative', paddingRight: '4.5rem', opacity: alert.is_active ? 1 : 0.5 }}>
      <span className="metric">{alert.metric.toUpperCase()}</span>
      <span className="operator">{alert.operator}</span>
      {isEditing ? (
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          <input
            type="number"
            step="0.01"
            className="target-edit-input"
            autoFocus
            value={editingValue}
            onChange={(e) => setEditingValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                handleSave();
              } else if (e.key === 'Escape') {
                setIsEditing(false);
              }
            }}
            style={{ width: '80px', padding: '2px 4px', fontSize: 'inherit' }}
          />
          <button type="button" className="btn-success" style={{ padding: '2px 6px', fontSize: '0.8rem', minWidth: 'auto', height: 'auto' }} onClick={handleSave}>✓</button>
          <button type="button" className="btn-danger" style={{ padding: '2px 6px', fontSize: '0.8rem', minWidth: 'auto', height: 'auto', display: 'inline-flex', alignItems: 'center' }} onClick={() => setIsEditing(false)}>✕</button>
        </div>
      ) : (
        <span 
          className="target"
          style={{ cursor: 'pointer', borderBottom: '1px dashed currentColor' }}
          title="Click para editar"
          onClick={() => {
            setEditingValue(alert.target.toString());
            setIsEditing(true);
          }}
        >
          {alert.target}{isRelative ? '%' : ''}
        </span>
      )}
      
      {isRelative && alert.reference_value !== null && alert.reference_value !== undefined && (
        <span style={{ marginLeft: '4px', fontSize: '0.8em', color: 'var(--primary)' }}>
          (Ref: {alert.reference_value.toFixed(2)})
        </span>
      )}
      
      {alert.current_value !== undefined && alert.current_value !== null && (
        <span className="current-val" style={{ marginLeft: '6px', fontSize: '0.85em', color: '#94a3b8' }}>
          (Current: {alert.current_value.toFixed(2)})
        </span>
      )}
      
      <div style={{ position: 'absolute', right: '0', top: '50%', transform: 'translateY(-50%)', display: 'flex', gap: '4px' }}>
        {onToggle && (
           <button
            type="button"
            className="btn-delete-alert"
            style={{ color: alert.is_active ? '#94a3b8' : '#eab308' }}
            onClick={() => onToggle(alert.id, !alert.is_active)}
            title={alert.is_active ? "Silenciar alerta" : "Activar alerta"}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              {alert.is_active ? (
                <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path>
              ) : (
                <g><path d="M13.73 21a2 2 0 0 1-3.46 0"></path><path d="M18.63 13A17.89 17.89 0 0 1 18 8"></path><path d="M6.26 6.26A5.86 5.86 0 0 0 6 8c0 7-3 9-3 9h14"></path><path d="M18 8a6 6 0 0 0-9.33-5"></path><line x1="1" y1="1" x2="23" y2="23"></line></g>
              )}
            </svg>
          </button>
        )}
        <button
          type="button"
          className="btn-delete-alert"
          onClick={() => onDelete(symbol, alert.metric)}
          title="Eliminar alerta"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M3 6h18"></path>
            <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"></path>
            <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"></path>
            <line x1="10" y1="11" x2="10" y2="17"></line>
            <line x1="14" y1="11" x2="14" y2="17"></line>
          </svg>
        </button>
      </div>
    </li>
  );
}
