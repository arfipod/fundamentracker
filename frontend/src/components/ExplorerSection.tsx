import React, { useState, useEffect, useRef } from 'react';
import { MetricChart } from './MetricChart';
import { MetricSelect } from './MetricSelect';
import { DataQualityBadge } from './DataQualityBadge';
import { apiFetch } from '../lib/apiClient';
import { getMetricLabel, type MetricCatalogItem } from '../types/metrics';
import type { DataQualityMetadata } from '../types/watchlist';

interface ExplorerSectionProps {
  metrics: MetricCatalogItem[];
}

interface CurrentMetric extends DataQualityMetadata {
  value: number | null;
}

/**
 * ExplorerSection component allows users to search for any stock ticker
 * and view current and historical data for a selected metric.
 * It uses an autocomplete search to help find tickers.
 * 
 * @returns {JSX.Element} The rendered ExplorerSection component
 */
export function ExplorerSection({ metrics }: ExplorerSectionProps) {
  const [ticker, setTicker] = useState('AAPL');
  const [metric, setMetric] = useState('price');
  
  const [searchResults, setSearchResults] = useState<{symbol: string, name: string}[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const [currentValue, setCurrentValue] = useState<number | null>(null);
  const [currentMetric, setCurrentMetric] = useState<CurrentMetric | null>(null);
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
    const historyMetrics = metrics.filter(item => item.supported_for_history);
    if (historyMetrics.length > 0 && !historyMetrics.some(item => item.key === metric)) {
      setMetric(historyMetrics[0].key);
    }
  }, [metrics, metric]);

  useEffect(() => {
    const fetchSearch = async () => {
      if (ticker.trim().length > 0 && showDropdown) {
        try {
          const res = await apiFetch(`/search?q=${ticker}`);
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
      const metricRes = await apiFetch(`/metric-current?ticker=${ticker}&metric=${metric}`);
      if (metricRes.ok) {
        const metricData = await metricRes.json();
        setCurrentValue(metricData.value);
        setCurrentMetric({
          value: metricData.value,
          source: metricData.source,
          as_of_date: metricData.as_of_date,
          fetched_at: metricData.fetched_at,
          expires_at: metricData.expires_at,
          stale: metricData.stale,
          confidence: metricData.confidence,
        });
      } else {
        setCurrentValue(null);
        setCurrentMetric(null);
      }
    } catch (err: any) {
      console.error(err.message || "An error occurred");
      setCurrentValue(null);
      setCurrentMetric(null);
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
            <MetricSelect metrics={metrics} value={metric} onChange={setMetric} support="history" />
          </div>
          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? 'Loading...' : 'Explore'}
          </button>
        </form>
      </section>

      <div className="explorer-content">
        <div className="current-value-card">
          <h3>Current {getMetricLabel(metrics, metric)}</h3>
          <div className="value">
            {currentValue !== null && currentValue !== undefined 
              ? (typeof currentValue === 'number' ? currentValue.toLocaleString(undefined, { maximumFractionDigits: 4 }) : currentValue) 
              : 'N/A'}
          </div>
          {currentMetric && (
            <DataQualityBadge
              metadata={{
                source: currentMetric.source,
                as_of_date: currentMetric.as_of_date,
                fetched_at: currentMetric.fetched_at,
                expires_at: currentMetric.expires_at,
                stale: currentMetric.stale,
                confidence: currentMetric.confidence,
              }}
            />
          )}
        </div>

        <div className="chart-container">
          <MetricChart ticker={ticker} metric={metric} currentValue={currentValue} height={400} />
        </div>
      </div>
    </div>
  );
}
