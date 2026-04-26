import React, { useState, useEffect, useRef } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend
} from 'recharts';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface HistoryData {
  date: string;
  value: number;
}

export function ExplorerSection() {
  const [ticker, setTicker] = useState('AAPL');
  const [metric, setMetric] = useState('price');
  
  const [searchResults, setSearchResults] = useState<{symbol: string, name: string}[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const [currentValue, setCurrentValue] = useState<number | null>(null);
  const [historyData, setHistoryData] = useState<HistoryData[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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

  const fetchData = async () => {
    if (!ticker) return;
    
    setLoading(true);
    setError(null);
    
    try {
      // Fetch current value
      const metricRes = await fetch(`${API_URL}/metric-current?ticker=${ticker}&metric=${metric}`);
      if (metricRes.ok) {
        const metricData = await metricRes.json();
        setCurrentValue(metricData.value);
      } else {
        setCurrentValue(null);
      }

      // Fetch history (fallback to price)
      const histRes = await fetch(`${API_URL}/history?ticker=${ticker}&metric=${metric}`);
      if (histRes.ok) {
        const histData = await histRes.json();
        setHistoryData(histData);
      } else {
        setHistoryData([]);
        const errorData = await histRes.json();
        setError(errorData.detail || "Failed to fetch historical data");
      }
    } catch (err: any) {
      setError(err.message || "An error occurred");
      setHistoryData([]);
      setCurrentValue(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [metric]); // Re-fetch on metric change

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setShowDropdown(false);
    fetchData();
  };

  return (
    <div className="explorer-section">
      <section className="form-section">
        <h2>Fundamental Explorer</h2>
        <form onSubmit={handleSearchSubmit} className="alert-form">
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
          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? 'Loading...' : 'Explore'}
          </button>
        </form>
      </section>

      <div className="explorer-content">
        <div className="current-value-card">
          <h3>Current {metric.toUpperCase()}</h3>
          <div className="value">
            {currentValue !== null && currentValue !== undefined 
              ? (typeof currentValue === 'number' ? currentValue.toLocaleString(undefined, { maximumFractionDigits: 4 }) : currentValue) 
              : 'N/A'}
          </div>
        </div>

        <div className="chart-container">
          <h3>Historical Evolution {metric !== 'price' ? '(Price Fallback)' : ''}</h3>
          {loading ? (
            <div className="loading">Loading chart data...</div>
          ) : error ? (
            <div className="error-message">{error}</div>
          ) : historyData.length > 0 ? (
            <div style={{ width: '100%', height: 400 }}>
              <ResponsiveContainer>
                <LineChart data={historyData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis 
                    dataKey="date" 
                    stroke="#94a3b8" 
                    tickFormatter={(val) => {
                      const date = new Date(val);
                      return `${date.getMonth() + 1}/${date.getFullYear().toString().slice(2)}`;
                    }}
                  />
                  <YAxis stroke="#94a3b8" domain={['auto', 'auto']} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', color: '#f8fafc' }}
                    itemStyle={{ color: '#60a5fa' }}
                  />
                  <Legend />
                  <Line 
                    type="monotone" 
                    dataKey="value" 
                    name={metric === 'price' ? 'Price' : `Price (Fallback for ${metric.toUpperCase()})`} 
                    stroke="#3b82f6" 
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 8 }} 
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="empty-message">No historical data available</div>
          )}
        </div>
      </div>
    </div>
  );
}
