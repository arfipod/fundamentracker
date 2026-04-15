import React, { useState, useEffect, useRef } from 'react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface Props {
  onAdd: (ticker: string, metric: string, operator: string, targetValue: number, alertType: string) => Promise<boolean>;
}

export function AlertForm({ onAdd }: Props) {
  const [ticker, setTicker] = useState('');
  const [metric, setMetric] = useState('pe');
  const [operator, setOperator] = useState('<');
  const [targetValue, setTargetValue] = useState('');
  const [alertType, setAlertType] = useState('absolute');

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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ticker || !targetValue) return;

    const success = await onAdd(ticker, metric, operator, parseFloat(targetValue), alertType);
    if (success) {
      setTicker('');
      setTargetValue('');
    }
  };

  return (
    <section className="form-section">
      <h2>Add Alert</h2>
      <form onSubmit={handleSubmit} className="alert-form">
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
          <label>Type</label>
          <select value={alertType} onChange={e => setAlertType(e.target.value)}>
            <option value="absolute">Absolute Value</option>
            <option value="relative">Change (%)</option>
          </select>
        </div>
        <div className="form-group">
          <label>{alertType === 'relative' ? 'Target (%)' : 'Target'}</label>
          <input 
            type="number" 
            step="any"
            placeholder={alertType === 'relative' ? "e.g. 5" : "e.g. 15.5"} 
            value={targetValue} 
            onChange={e => setTargetValue(e.target.value)} 
            required
          />
        </div>
        <button type="submit" className="btn-success">Add Alert</button>
      </form>
    </section>
  );
}
