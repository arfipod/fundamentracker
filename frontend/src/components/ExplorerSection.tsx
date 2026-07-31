import React, { useState, useEffect, useRef } from 'react';
import { MetricChart } from './MetricChart';
import { MetricSelect } from './MetricSelect';
import { DataQualityBadge } from './DataQualityBadge';
import { apiFetch } from '../lib/apiClient';
import { formatMetricValue, getMetricLabel, type MetricCatalogItem } from '../types/metrics';
import type { DataQualityMetadata } from '../types/watchlist';

interface ExplorerSectionProps {
  metrics: MetricCatalogItem[];
}

interface CurrentMetric extends DataQualityMetadata {
  value: number | null;
}

/**
 * ExplorerSection allows users to inspect every supported current metric and,
 * when available, its real historical series.
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
  const selectedMetric = metrics.find(item => item.key === metric);

  useEffect(() => {
    const handleOutsideClick = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleOutsideClick);
    return () => document.removeEventListener('mousedown', handleOutsideClick);
  }, []);

  useEffect(() => {
    if (metrics.length > 0 && !metrics.some(item => item.key === metric)) {
      setMetric(metrics[0].key);
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
        } catch (error) {
          console.error(error);
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
    } catch (error) {
      console.error(error instanceof Error ? error.message : 'An error occurred');
      setCurrentValue(null);
      setCurrentMetric(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [metric]);

  const handleSearchSubmit = (event: React.FormEvent) => {
    event.preventDefault();
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
              onChange={event => {
                setTicker(event.target.value.toUpperCase());
                setShowDropdown(true);
              }}
              onFocus={() => {
                if (ticker.length > 0) setShowDropdown(true);
              }}
              required
            />
            {showDropdown && searchResults.length > 0 && (
              <ul className="autocomplete-dropdown">
                {searchResults.map((result, index) => (
                  <li key={index} onClick={() => handleSelectResult(result.symbol)}>
                    <span className="ac-symbol">{result.symbol}</span>
                    <span className="ac-name">{result.name}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <div className="form-group">
            <label>Metric</label>
            <MetricSelect metrics={metrics} value={metric} onChange={setMetric} support="all" />
          </div>
          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? 'Loading...' : 'Explore'}
          </button>
        </form>
      </section>

      <div className="explorer-content">
        <div className="current-value-card">
          <h3>Current {getMetricLabel(metrics, metric)}</h3>
          <div className="value">{formatMetricValue(metrics, metric, currentValue)}</div>
          {selectedMetric?.description && (
            <p style={{ margin: '0.75rem 0', color: 'var(--muted-text, #94a3b8)', lineHeight: 1.5 }}>
              {selectedMetric.description}
            </p>
          )}
          {selectedMetric && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '0.75rem' }}>
              {selectedMetric.period && <span className="badge">Period: {selectedMetric.period}</span>}
              {selectedMetric.source_kind && <span className="badge">Source: {selectedMetric.source_kind}</span>}
              {!selectedMetric.supported_for_history && <span className="badge">Current only</span>}
            </div>
          )}
          {selectedMetric?.formula && (
            <div style={{ fontSize: '0.8rem', color: 'var(--muted-text, #94a3b8)', marginBottom: '0.75rem' }}>
              Formula: {selectedMetric.formula}
            </div>
          )}
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
          {selectedMetric?.supported_for_history ? (
            <MetricChart ticker={ticker} metric={metric} currentValue={currentValue} height={400} />
          ) : (
            <div
              className="empty-message"
              style={{ height: 400, display: 'flex', alignItems: 'center', justifyContent: 'center', textAlign: 'center' }}
            >
              This metric is calculated from the latest statements or analyst data. A reliable historical series is not exposed yet.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
