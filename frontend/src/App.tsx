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

  // Form states
  const [ticker, setTicker] = useState('');
  const [metric, setMetric] = useState('pe');
  const [operator, setOperator] = useState('<');
  const [targetValue, setTargetValue] = useState('');

  // Autocomplete states
  const [searchResults, setSearchResults] = useState<{symbol: string, name: string}[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

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

  useEffect(() => {
    fetchWatchlist();
  }, []);

  const handleAddAlert = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ticker || !targetValue) return;

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
        <button className="btn-primary" onClick={handleScan}>
          Force Scan
        </button>
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
                          <li key={idx}>
                            <span className="metric">{alert.metric.toUpperCase()}</span>
                            <span className="operator">{alert.operator}</span>
                            <span className="target">{alert.target}</span>
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
