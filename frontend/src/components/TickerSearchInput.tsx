import { useEffect, useId, useRef, useState } from 'react';
import { apiFetch } from '../lib/apiClient';
import { Icon } from './Icon';

interface SearchResult {
  symbol: string;
  name: string;
}

interface TickerSearchInputProps {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  helpText?: string;
  required?: boolean;
}

export function TickerSearchInput({ id, label, value, onChange, placeholder = 'AAPL', helpText, required = false }: TickerSearchInputProps) {
  const generatedId = useId();
  const listboxId = `${id}-${generatedId}-results`;
  const helpId = helpText ? `${id}-${generatedId}-help` : undefined;
  const wrapperRef = useRef<HTMLDivElement>(null);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);

  useEffect(() => {
    const handleOutsidePointer = (event: PointerEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target as Node)) {
        setOpen(false);
        setActiveIndex(-1);
      }
    };
    document.addEventListener('pointerdown', handleOutsidePointer);
    return () => document.removeEventListener('pointerdown', handleOutsidePointer);
  }, []);

  useEffect(() => {
    const query = value.trim();
    if (!open || query.length === 0) {
      setResults([]);
      setLoading(false);
      return;
    }

    const controller = new AbortController();
    const timeout = window.setTimeout(async () => {
      setLoading(true);
      try {
        const response = await apiFetch(`/search?q=${encodeURIComponent(query)}`, { signal: controller.signal });
        if (!response.ok) {
          setResults([]);
          return;
        }
        const data = (await response.json()) as SearchResult[];
        setResults(data);
        setActiveIndex(data.length > 0 ? 0 : -1);
      } catch (error) {
        if (!(error instanceof DOMException && error.name === 'AbortError')) {
          setResults([]);
        }
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }, 250);

    return () => {
      window.clearTimeout(timeout);
      controller.abort();
    };
  }, [open, value]);

  const selectResult = (result: SearchResult) => {
    onChange(result.symbol.toUpperCase());
    setOpen(false);
    setResults([]);
    setActiveIndex(-1);
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Escape') {
      setOpen(false);
      setActiveIndex(-1);
      return;
    }
    if (!open || results.length === 0) {
      if (event.key === 'ArrowDown') setOpen(true);
      return;
    }
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setActiveIndex((current) => (current + 1) % results.length);
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      setActiveIndex((current) => (current <= 0 ? results.length - 1 : current - 1));
    } else if (event.key === 'Enter' && activeIndex >= 0) {
      event.preventDefault();
      selectResult(results[activeIndex]);
    }
  };

  const hasPopup = open && (loading || results.length > 0);

  return (
    <div className="field autocomplete" ref={wrapperRef}>
      <label htmlFor={id}>{label}</label>
      <div className="input-with-icon">
        <Icon name="search" size={17} />
        <input
          id={id}
          type="text"
          role="combobox"
          autoComplete="off"
          aria-autocomplete="list"
          aria-controls={hasPopup ? listboxId : undefined}
          aria-describedby={helpId}
          aria-expanded={hasPopup}
          aria-activedescendant={activeIndex >= 0 ? `${listboxId}-${activeIndex}` : undefined}
          placeholder={placeholder}
          value={value}
          onChange={(event) => {
            onChange(event.target.value.toUpperCase());
            setOpen(true);
          }}
          onFocus={() => { if (value.trim()) setOpen(true); }}
          onKeyDown={handleKeyDown}
          required={required}
        />
      </div>
      {helpText && <span className="field-help" id={helpId}>{helpText}</span>}
      {hasPopup && (
        <ul className="autocomplete-menu" id={listboxId} role="listbox">
          {loading ? (
            <li className="autocomplete-status" role="option" aria-selected="false">Searching…</li>
          ) : (
            results.map((result, index) => (
              <li
                className={index === activeIndex ? 'active' : undefined}
                id={`${listboxId}-${index}`}
                key={result.symbol}
                role="option"
                aria-selected={index === activeIndex}
                onMouseEnter={() => setActiveIndex(index)}
                onMouseDown={(event) => {
                  event.preventDefault();
                  selectResult(result);
                }}
              >
                <strong>{result.symbol}</strong>
                <span>{result.name}</span>
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  );
}
