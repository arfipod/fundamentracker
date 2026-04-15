import { useEffect, useState, useRef } from 'react';
import './App.css';

interface Alert {
  metric: string;
  operator: string;
  target: number;
  is_triggered?: boolean;
  current_value?: number | null;
}

interface TickerData {
  name: string;
  alerts: Alert[];
}

interface Watchlist {
  [key: string]: TickerData;
}

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function App() {
  const [watchlist, setWatchlist] = useState<Watchlist | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [scanInterval, setScanInterval] = useState<number>(0);
  const [lastScanTime, setLastScanTime] = useState<number>(0);
  const [isScanning, setIsScanning] = useState(false);

  // Form states
  const [ticker, setTicker] = useState('');
  const [metric, setMetric] = useState('pe');
  const [operator, setOperator] = useState('<');
  const [targetValue, setTargetValue] = useState('');

  // Autocomplete states
  const [searchResults, setSearchResults] = useState<{symbol: string, name: string}[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Inline editing state
  const [editingAlert, setEditingAlert] = useState<{ticker: string, metric: string} | null>(null);
  const [editingValue, setEditingValue] = useState<string>('');
  
  // Stopwatch interval state
  const [localInterval, setLocalInterval] = useState({ d: 0, h: 0, m: 0 });

  // Inline Metric Add
  const [addingMetricFor, setAddingMetricFor] = useState<string | null>(null);

  const nextScanTime = (scanInterval > 0 && lastScanTime > 0) ? lastScanTime + scanInterval : 0;

  useEffect(() => {
    setLocalInterval({
      d: Math.floor(scanInterval / 86400),
      h: Math.floor((scanInterval % 86400) / 3600),
      m: Math.floor((scanInterval % 3600) / 60)
    });
  }, [scanInterval]);

  const handleApplyInterval = () => {
    const total = (localInterval.d * 86400) + (localInterval.h * 3600) + (localInterval.m * 60);
    if (total !== scanInterval) {
      handleUpdateInterval(total);
    }
  };

  useEffect(() => {
    const handleOutsideClick = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener("mousedown", handleOutsideClick);
    return () => document.removeEventListener("mousedown", handleOutsideClick);
  }, []);

  useEffect(() => {
    const fetchSearch = async () => {
      if (ticker.trim().length > 0 && showDropdown) {
        try {
          const res = await fetch(`${API_URL}/search?q=${ticker}`);
          if (res.ok) {
            const data = await res.json();
            setSearchResults(data);
          }
        } catch (e) {
          console.error(e);
        }
      } else {
        setSearchResults([]);
      }
    };
    const timeout = setTimeout(fetchSearch, 300);
    return () => clearTimeout(timeout);
  }, [ticker, showDropdown]);

  const handleSelectResult = (symbol: string) => {
    setTicker(symbol.toUpperCase());
    setShowDropdown(false);
  };

  const fetchWatchlist = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_URL}/watchlist`);
      if (!response.ok) throw new Error('Error loading the watchlist');
      const result = await response.json();
      setWatchlist(result);
      setError(null);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Unknown error');
      }
    } finally {
      setLoading(false);
    }
  };

  const fetchScanSettings = async () => {
    try {
      const response = await fetch(`${API_URL}/scan-settings`);
      if (response.ok) {
        const data = await response.json();
        setScanInterval(data.interval_seconds || 0);
        setLastScanTime(data.last_scan_time || 0);
      }
    } catch (err) {
      console.error("Error loading scan settings", err);
    }
  };

  const handleUpdateInterval = async (newInterval: number) => {
    setScanInterval(newInterval);
    try {
      await fetch(`${API_URL}/scan-settings`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ interval_seconds: newInterval })
      });
    } catch (err) {
      console.error("Error saving scan settings", err);
    }
  };

  useEffect(() => {
    fetchWatchlist();
    fetchScanSettings();
  }, []);

  const handleAddAlert = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ticker || !targetValue) return;

    if (watchlist && watchlist[ticker]) {
      const existingAlerts = watchlist[ticker].alerts || [];
      const hasMetric = existingAlerts.some(a => a.metric === metric);
      if (hasMetric) {
        if (!window.confirm("Ya tienes esta métrica configurada para esta empresa. ¿Deseas agregarla de todas formas?")) {
          return;
        }
      } else {
        if (!window.confirm("Esta empresa ya está en tu lista. ¿Deseas agregar una nueva métrica para ella?")) {
          return;
        }
      }
    }

    try {
      const response = await fetch(`${API_URL}/add`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ticker,
          metric,
          operator,
          value: parseFloat(targetValue),
        }),
      });
      if (!response.ok) throw new Error('Error adding the alert');
      
      // Clear form
      setTicker('');
      setTargetValue('');
      await fetchWatchlist();
      await fetchScanSettings();
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      }
    }
  };

  const handleAddAlertInline = async (tickerToAdd: string, metricToAdd: string, operatorToAdd: string, targetValueToAdd: number) => {
    if (watchlist && watchlist[tickerToAdd]) {
      const hasMetric = watchlist[tickerToAdd].alerts.some(a => a.metric === metricToAdd);
      if (hasMetric) {
        if (!window.confirm("Ya tienes esta métrica configurada para esta empresa. ¿Deseas agregarla de todas formas?")) {
          return;
        }
      }
    }

    try {
      const response = await fetch(`${API_URL}/add`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ticker: tickerToAdd,
          metric: metricToAdd,
          operator: operatorToAdd,
          value: targetValueToAdd,
        }),
      });
      if (!response.ok) throw new Error('Error adding the alert');
      
      setAddingMetricFor(null);
      await fetchWatchlist();
      await fetchScanSettings();
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      }
    }
  };

  const handleUpdateTarget = async (tickerToUpdate: string, metricToUpdate: string, newValue: number) => {
    try {
      const response = await fetch(`${API_URL}/update`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ticker: tickerToUpdate,
          metric: metricToUpdate,
          value: newValue,
        }),
      });
      if (!response.ok) throw new Error('Error updating alert');
      await fetchWatchlist();
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      }
    } finally {
      setEditingAlert(null);
    }
  };

  const handleDeleteAlert = async (tickerToDelete: string, metricToDelete: string) => {
    try {
      const response = await fetch(`${API_URL}/remove/${tickerToDelete}/${metricToDelete}`, {
        method: 'DELETE',
      });
      if (!response.ok) throw new Error('Error removing the alert');
      await fetchWatchlist();
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      }
    }
  };

  const handleScan = async () => {
    try {
      setIsScanning(true);
      const response = await fetch(`${API_URL}/scan`, { method: 'POST' });
      if (!response.ok) throw new Error('Error scanning');
      await fetchWatchlist();
      await fetchScanSettings();
    } catch (err: unknown) {
       if (err instanceof Error) {
        setError(err.message);
      }
    } finally {
      setIsScanning(false);
    }
  };

  const handleDelete = async (tickerToDelete: string) => {
    try {
      const response = await fetch(`${API_URL}/remove/${tickerToDelete}`, {
        method: 'DELETE',
      });
      if (!response.ok) throw new Error('Error removing the ticker');
      await fetchWatchlist();
    } catch (err: unknown) {
       if (err instanceof Error) {
        setError(err.message);
      }
    }
  };

  return (
    <div className="dashboard">
      <header className="header">
        <h1>FundamenTracker Dashboard</h1>
        <div className="header-actions" style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <div className="scan-interval-selector" style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '0.4rem', backgroundColor: 'var(--panel-bg)', padding: '0.4rem 0.8rem', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
            <label style={{ fontSize: '0.85rem', color: 'var(--text-muted)', fontWeight: 600, marginRight: '0.5rem' }}>Auto-Scan:</label>
            <div style={{ display: 'flex', alignItems: 'center', gap: '2px' }}>
              <input 
                type="number" min="0" className="stopwatch-input" value={localInterval.d}
                onChange={e => setLocalInterval({...localInterval, d: Number(e.target.value)})}
                onBlur={handleApplyInterval}
              /><span className="stopwatch-label">d</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '2px' }}>
              <input 
                type="number" min="0" max="23" className="stopwatch-input" value={localInterval.h}
                onChange={e => setLocalInterval({...localInterval, h: Number(e.target.value)})}
                onBlur={handleApplyInterval}
              /><span className="stopwatch-label">h</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '2px' }}>
              <input 
                type="number" min="0" max="59" className="stopwatch-input" value={localInterval.m}
                onChange={e => setLocalInterval({...localInterval, m: Number(e.target.value)})}
                onBlur={handleApplyInterval}
              /><span className="stopwatch-label">m</span>
            </div>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '0.4rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              {isScanning && <span style={{ fontSize: '0.85rem', color: 'var(--primary)', fontWeight: 'bold' }}>Scanning...</span>}
              <button className="btn-primary" onClick={handleScan} disabled={isScanning}>
                Force Scan
              </button>
            </div>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Last scan: {lastScanTime ? new Date(lastScanTime * 1000).toLocaleString() : 'Nunca'}
            </span>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Next scan: {nextScanTime ? new Date(nextScanTime * 1000).toLocaleString() : 'Manual'}
            </span>
          </div>
        </div>
      </header>

      {error && <div className="error-message">{error}</div>}

      <section className="form-section">
        <h2>Add Alert</h2>
        <form onSubmit={handleAddAlert} className="alert-form">
          <div className="form-group autocomplete-wrapper" ref={dropdownRef}>
            <label>Ticker</label>
            <input 
              type="text" 
              placeholder="e.g. AAPL" 
              value={ticker} 
              onChange={e => {
                setTicker(e.target.value.toUpperCase());
                setShowDropdown(true);
              }} 
              onFocus={() => {
                if (ticker.length > 0) setShowDropdown(true);
              }}
              required
            />
            {showDropdown && searchResults.length > 0 && (
              <ul className="autocomplete-dropdown">
                {searchResults.map((res, i) => (
                  <li key={i} onClick={() => handleSelectResult(res.symbol)}>
                    <span className="ac-symbol">{res.symbol}</span>
                    <span className="ac-name">{res.name}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <div className="form-group">
            <label>Metric</label>
            <select value={metric} onChange={e => setMetric(e.target.value)}>
              <option value="pe">PE</option>
              <option value="fpe">FPE</option>
              <option value="pb">PB</option>
              <option value="evebitda">EV/EBITDA</option>
              <option value="roe">ROE</option>
              <option value="price">Price</option>
            </select>
          </div>
          <div className="form-group">
            <label>Operator</label>
            <select value={operator} onChange={e => setOperator(e.target.value)}>
              <option value="<">&lt;</option>
              <option value=">">&gt;</option>
              <option value="<=">&lt;=</option>
              <option value=">=">&gt;=</option>
              <option value="==">==</option>
              <option value="!=">!=</option>
            </select>
          </div>
          <div className="form-group">
            <label>Target</label>
            <input 
              type="number" 
              step="any"
              placeholder="e.g. 15.5" 
              value={targetValue} 
              onChange={e => setTargetValue(e.target.value)} 
              required
            />
          </div>
          <button type="submit" className="btn-success">Add Alert</button>
        </form>
      </section>

      <section className="watchlist-section">
        <h2>Watchlist</h2>
        {loading ? (
          <div className="loading">Loading data...</div>
        ) : (
          <div className="grid-container">
            {watchlist && Object.entries(watchlist).length > 0 ? (
              Object.entries(watchlist).map(([symbol, data]) => (
                <div key={symbol} className="card">
                  <div className="card-header">
                    <div className="card-title-group">
                      <h3>{symbol}</h3>
                      <p className="company-name">{data.name}</p>
                    </div>
                    <button 
                      type="button"
                      className="btn-danger" 
                      onClick={() => handleDelete(symbol)}
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
                      <button type="button" onClick={() => setAddingMetricFor(symbol)} style={{ background: 'transparent', border: '1px dashed var(--primary)', color: 'var(--primary)', cursor: 'pointer', borderRadius: '4px', padding: '2px 8px', fontSize: '0.8rem', fontWeight: 'bold' }}>+ Metric</button>
                    </div>

                    {addingMetricFor === symbol && (
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
                        <input type="number" step="any" placeholder="Valor" id={`inline-t-${symbol}`} className="target-edit-input" style={{ width: '60px', padding: '2px 4px' }} />
                        <div style={{ display: 'flex', gap: '4px' }}>
                          <button className="btn-success" style={{ padding: '2px 6px', fontSize: '0.8rem' }} onClick={() => {
                            const m = (document.getElementById(`inline-m-${symbol}`) as HTMLSelectElement).value;
                            const o = (document.getElementById(`inline-o-${symbol}`) as HTMLSelectElement).value;
                            const t = (document.getElementById(`inline-t-${symbol}`) as HTMLInputElement).value;
                            if (t) handleAddAlertInline(symbol, m, o, parseFloat(t));
                          }}>✓</button>
                          <button className="btn-danger" style={{ padding: '2px 6px', fontSize: '0.8rem' }} onClick={() => setAddingMetricFor(null)}>✕</button>
                        </div>
                      </div>
                    )}

                    {data.alerts && data.alerts.length > 0 ? (
                      <ul className="alerts-list">
                        {data.alerts.map((alert, idx) => (
                          <li key={idx} style={{ position: 'relative', paddingRight: '2.5rem' }}>
                            <span className="metric">{alert.metric.toUpperCase()}</span>
                            <span className="operator">{alert.operator}</span>
                            {editingAlert?.ticker === symbol && editingAlert?.metric === alert.metric ? (
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
                                      const val = parseFloat(parseFloat(editingValue).toFixed(2));
                                      if (!isNaN(val)) handleUpdateTarget(symbol, alert.metric, val);
                                    } else if (e.key === 'Escape') {
                                      setEditingAlert(null);
                                    }
                                  }}
                                  style={{ width: '80px', padding: '2px 4px', fontSize: 'inherit' }}
                                />
                                <button type="button" className="btn-success" style={{ padding: '2px 6px', fontSize: '0.8rem', minWidth: 'auto', height: 'auto' }} onClick={() => {
                                  const val = parseFloat(parseFloat(editingValue).toFixed(2));
                                  if (!isNaN(val)) handleUpdateTarget(symbol, alert.metric, val);
                                }}>✓</button>
                                <button type="button" className="btn-danger" style={{ padding: '2px 6px', fontSize: '0.8rem', minWidth: 'auto', height: 'auto', display: 'inline-flex', alignItems: 'center' }} onClick={() => setEditingAlert(null)}>✕</button>
                              </div>
                            ) : (
                              <span 
                                className="target"
                                style={{ cursor: 'pointer', borderBottom: '1px dashed currentColor' }}
                                title="Click para editar"
                                onClick={() => {
                                  setEditingAlert({ ticker: symbol, metric: alert.metric });
                                  setEditingValue(alert.target.toString());
                                }}
                              >
                                {alert.target}
                              </span>
                            )}
                            {alert.current_value !== undefined && alert.current_value !== null && (
                              <span className="current-val" style={{ marginLeft: '6px', fontSize: '0.85em', color: '#94a3b8' }}>
                                (Current: {alert.current_value.toFixed(2)})
                              </span>
                            )}
                            <button
                              type="button"
                              className="btn-delete-alert"
                              onClick={() => handleDeleteAlert(symbol, alert.metric)}
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
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="no-alerts">No alerts</p>
                    )}
                  </div>
                </div>
              ))
            ) : (
              <p className="empty-message">No tickers in the watchlist.</p>
            )}
          </div>
        )}
      </section>
    </div>
  );
}

export default App;
