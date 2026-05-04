import React, { useState, useEffect, useRef } from 'react';
import { MetricChart } from './MetricChart';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * ExplorerSection component allows users to search for any stock ticker
 * and view current and historical data for a selected metric.
 * It uses an autocomplete search to help find tickers.
 * 
 * @returns {JSX.Element} The rendered ExplorerSection component
 */
export function ExplorerSection() {
  const [ticker, setTicker] = useState('AAPL');
  const [metric, setMetric] = useState('price');
  
  const [searchResults, setSearchResults] = useState<{symbol: string, name: string}[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const [currentValue, setCurrentValue] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);

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
    
    try {
      // Fetch current value
      const metricRes = await fetch(`${API_URL}/metric-current?ticker=${ticker}&metric=${metric}`);
      if (metricRes.ok) {
        const metricData = await metricRes.json();
        setCurrentValue(metricData.value);
      } else {
        setCurrentValue(null);
      }
    } catch (err: any) {
      console.error(err.message || "An error occurred");
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
              <option value="roic">ROIC</option>
              <option value="dividendyield">Dividend Yield</option>
              <option value="payoutratio">Payout Ratio</option>
              <option value="debttoequity">Debt to Equity</option>
              <option value="profitmargins">Profit Margins</option>
              <option value="operatingmargins">Operating Margins</option>
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
          <MetricChart ticker={ticker} metric={metric} currentValue={currentValue} height={400} />
        </div>
      </div>
    </div>
  );
}
