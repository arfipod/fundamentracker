import { useEffect, useState, useRef } from 'react';
import './App.css';

interface Alert {
  metric: string;
  operator: string;
  target: number;
  is_triggered?: boolean;
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
      const response = await fetch(`${API_URL}/scan`, { method: 'POST' });
      if (!response.ok) throw new Error('Error scanning');
      alert('Scan finished');
      await fetchWatchlist();
    } catch (err: unknown) {
       if (err instanceof Error) {
        setError(err.message);
      }
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
          <div className="scan-interval-selector" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <label style={{ fontSize: '0.85rem', color: 'var(--text-muted)', fontWeight: 600 }}>Auto-Scan:</label>
            <select 
              value={scanInterval} 
              onChange={(e) => handleUpdateInterval(Number(e.target.value))}
              style={{
                padding: '0.4rem 0.6rem',
                borderRadius: '6px',
                border: '1px solid var(--border-color)',
                backgroundColor: 'var(--input-bg)',
                color: 'var(--text-main)',
                fontSize: '0.9rem',
                cursor: 'pointer'
              }}
            >
              <option value={0}>Manual</option>
              <option value={60}>Cada 1 Minuto</option>
              <option value={300}>Cada 5 Minutos</option>
              <option value={3600}>Cada Hora</option>
              <option value={43200}>Cada 12 Horas</option>
              <option value={86400}>Cada Día</option>
            </select>
          </div>
          <button className="btn-primary" onClick={handleScan}>
            Force Scan
          </button>
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
                    <h4>Configured Alerts:</h4>
                    {data.alerts && data.alerts.length > 0 ? (
                      <ul className="alerts-list">
                        {data.alerts.map((alert, idx) => (
                          <li key={idx} style={{ position: 'relative', paddingRight: '2.5rem' }}>
                            <span className="metric">{alert.metric.toUpperCase()}</span>
                            <span className="operator">{alert.operator}</span>
                            {editingAlert?.ticker === symbol && editingAlert?.metric === alert.metric ? (
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
                                onBlur={() => {
                                  if (editingValue.trim() === '') {
                                    setEditingAlert(null);
                                    return;
                                  }
                                  const val = parseFloat(parseFloat(editingValue).toFixed(2));
                                  if (!isNaN(val)) handleUpdateTarget(symbol, alert.metric, val);
                                  else setEditingAlert(null);
                                }}
                                style={{ width: '80px', padding: '2px 4px', fontSize: 'inherit' }}
                              />
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
