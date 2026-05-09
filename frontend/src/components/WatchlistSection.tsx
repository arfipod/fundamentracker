import { useState, useMemo } from 'react';
import type { Watchlist, WatchlistMetadata } from '../types/watchlist';
import type { MetricCatalogItem } from '../types/metrics';
import { TickerRow } from './TickerRow';
import { TickerCard } from './TickerCard';

/**
 * Props for the WatchlistSection component.
 * @interface Props
 * @property {Watchlist | null} watchlist - The user's configured watchlist data.
 * @property {boolean} loading - Whether the watchlist data is currently loading.
 * @property {Function} onDeleteTicker - Callback to delete a whole ticker from the watchlist.
 * @property {Function} onAddInline - Callback to add a new alert metric inline.
 * @property {Function} onUpdateAlert - Callback to update the target value of an alert.
 * @property {Function} onDeleteAlert - Callback to delete a specific alert.
 * @property {Function} onToggleAlert - Callback to toggle the active status of an alert.
 */
interface Props {
  watchlist: Watchlist | null;
  loading: boolean;
  metrics: MetricCatalogItem[];
  onDeleteTicker: (ticker: string) => void;
  onAddInline: (ticker: string, metric: string, operator: string, val: number, alertType?: string) => void;
  onUpdateAlert: (alertId: string, val: number) => void;
  onDeleteAlert: (alertId: string, ticker: string) => void;
  onToggleAlert: (alertId: string, isActive: boolean) => void;
  onAddTag: (ticker: string, name: string) => void;
  onRemoveTag: (ticker: string, tagNameOrId: string) => void;
  onUpdateMetadata: (ticker: string, metadata: Partial<WatchlistMetadata>) => void;
}

type SortField = 'symbol' | 'name' | 'alerts';
type SortDir = 'asc' | 'desc';
type ViewMode = 'details' | 'grid';

/**
 * WatchlistSection component renders the main area for the user's tracked stocks and alerts.
 * It provides both a detailed table view and a grid card view, and supports sorting.
 * 
 * @param {Props} props - The component props
 * @returns {JSX.Element} The rendered WatchlistSection component
 */
export function WatchlistSection({
  watchlist,
  loading,
  metrics,
  onDeleteTicker,
  onAddInline,
  onUpdateAlert,
  onDeleteAlert,
  onToggleAlert,
  onAddTag,
  onRemoveTag,
  onUpdateMetadata
}: Props) {
  const [sortField, setSortField] = useState<SortField>('symbol');
  const [sortDir, setSortDir] = useState<SortDir>('asc');
  const [viewMode, setViewMode] = useState<ViewMode>('details');
  const [filterTag, setFilterTag] = useState<string>('');

  const allTags = useMemo(() => {
    const tagsSet = new Set<string>();
    Object.values(watchlist || {}).forEach(data => {
      data.tags?.forEach(tag => tagsSet.add(tag.name));
    });
    return Array.from(tagsSet).sort();
  }, [watchlist]);

  const sortedWatchlist = useMemo(() => {
    if (!watchlist) return [];
    let entries = Object.entries(watchlist);
    
    if (filterTag) {
      entries = entries.filter(([, data]) => data.tags?.some(tag => tag.name === filterTag));
    }
    
    return entries.sort((a, b) => {
      let valA: string | number = a[1][sortField as keyof typeof a[1]] as any;
      let valB: string | number = b[1][sortField as keyof typeof b[1]] as any;
      
      if (sortField === 'symbol') {
        valA = a[0];
        valB = b[0];
      } else if (sortField === 'alerts') {
        valA = a[1].alerts?.length || 0;
        valB = b[1].alerts?.length || 0;
      }
      
      if (valA < valB) return sortDir === 'asc' ? -1 : 1;
      if (valA > valB) return sortDir === 'asc' ? 1 : -1;
      return 0;
    });
  }, [watchlist, sortField, sortDir, filterTag]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDir('asc');
    }
  };

  const getSortIcon = (field: SortField) => {
    if (sortField !== field) return <span style={{ opacity: 0.3, marginLeft: '4px' }}>↕</span>;
    return sortDir === 'asc' ? <span style={{ marginLeft: '4px' }}>↑</span> : <span style={{ marginLeft: '4px' }}>↓</span>;
  };

  return (
    <section className="watchlist-section">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <h2 style={{ margin: 0 }}>Watchlist</h2>
          {allTags.length > 0 && (
            <select 
              value={filterTag} 
              onChange={e => setFilterTag(e.target.value)}
              style={{ padding: '4px 8px', borderRadius: '4px', background: 'var(--bg-color)', color: 'var(--text-color)', border: '1px solid var(--border-color)' }}
            >
              <option value="">All Tags</option>
              {allTags.map(tag => <option key={tag} value={tag}>#{tag}</option>)}
            </select>
          )}
        </div>
        <div className="view-toggle">
          <button 
            className={`toggle-btn ${viewMode === 'details' ? 'active' : ''}`}
            onClick={() => setViewMode('details')}
            title="Details View"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="8" y1="6" x2="21" y2="6"></line>
              <line x1="8" y1="12" x2="21" y2="12"></line>
              <line x1="8" y1="18" x2="21" y2="18"></line>
              <line x1="3" y1="6" x2="3.01" y2="6"></line>
              <line x1="3" y1="12" x2="3.01" y2="12"></line>
              <line x1="3" y1="18" x2="3.01" y2="18"></line>
            </svg>
          </button>
          <button 
            className={`toggle-btn ${viewMode === 'grid' ? 'active' : ''}`}
            onClick={() => setViewMode('grid')}
            title="Grid View"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="3" width="7" height="7"></rect>
              <rect x="14" y="3" width="7" height="7"></rect>
              <rect x="14" y="14" width="7" height="7"></rect>
              <rect x="3" y="14" width="7" height="7"></rect>
            </svg>
          </button>
        </div>
      </div>
      
      {loading ? (
        <div className="loading">Loading data...</div>
      ) : (
        <>
          {watchlist && Object.entries(watchlist).length > 0 ? (
            viewMode === 'details' ? (
              <div className="table-container">
                <table className="details-table">
                  <thead>
                    <tr>
                      <th onClick={() => handleSort('symbol')} style={{ width: '15%' }}>
                        Symbol {getSortIcon('symbol')}
                      </th>
                      <th onClick={() => handleSort('name')} style={{ width: '35%' }}>
                        Name {getSortIcon('name')}
                      </th>
                      <th onClick={() => handleSort('alerts')} style={{ width: '40%' }}>
                        Configured Alerts {getSortIcon('alerts')}
                      </th>
                      <th style={{ width: '10%', textAlign: 'right' }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sortedWatchlist.map(([symbol, data]) => (
                      <TickerRow
                        key={symbol}
                        symbol={symbol}
                        data={data}
                        metrics={metrics}
                        onDeleteTicker={onDeleteTicker}
                        onAddInline={onAddInline}
                        onUpdateAlert={onUpdateAlert}
                        onDeleteAlert={onDeleteAlert}
                        onToggleAlert={onToggleAlert}
                        onAddTag={onAddTag}
                        onRemoveTag={onRemoveTag}
                        onUpdateMetadata={onUpdateMetadata}
                      />
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="grid-container">
                {sortedWatchlist.map(([symbol, data]) => (
                  <TickerCard
                    key={symbol}
                    symbol={symbol}
                    data={data}
                    metrics={metrics}
                    onDeleteTicker={onDeleteTicker}
                    onAddInline={onAddInline}
                    onUpdateAlert={onUpdateAlert}
                    onDeleteAlert={onDeleteAlert}
                    onToggleAlert={onToggleAlert}
                    onAddTag={onAddTag}
                    onRemoveTag={onRemoveTag}
                    onUpdateMetadata={onUpdateMetadata}
                  />
                ))}
              </div>
            )
          ) : (
            <p className="empty-message">No tickers in the watchlist.</p>
          )}
        </>
      )}
    </section>
  );
}
