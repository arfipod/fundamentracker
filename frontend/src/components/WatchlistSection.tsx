import { useMemo, useState } from 'react';
import type { Watchlist, WatchlistMetadata, TickerData } from '../types/watchlist';
import type { MetricCatalogItem } from '../types/metrics';
import { useMediaQuery } from '../hooks/useMediaQuery';
import { Icon } from './Icon';
import { TickerRow } from './TickerRow';
import { TickerCard } from './TickerCard';

interface Props {
  watchlist: Watchlist | null; loading: boolean; metrics: MetricCatalogItem[];
  onDeleteTicker: (ticker: string) => void;
  onAddInline: (ticker: string, metric: string, operator: string, val: number, alertType?: string) => void;
  onUpdateAlert: (alertId: string, val: number) => void;
  onDeleteAlert: (alertId: string, ticker: string) => void;
  onToggleAlert: (alertId: string, isActive: boolean) => void;
  onAddTag: (ticker: string, name: string) => void;
  onRemoveTag: (ticker: string, tagNameOrId: string) => void;
  onUpdateMetadata: (ticker: string, metadata: Partial<WatchlistMetadata>) => void;
}
type SortField = 'symbol' | 'name' | 'alerts'; type SortDirection = 'asc' | 'desc'; type ViewMode = 'details' | 'grid'; type WatchlistEntry = [string, TickerData];
function sortValue([symbol, data]: WatchlistEntry, field: SortField): string | number { if (field === 'symbol') return symbol.toLocaleLowerCase(); if (field === 'name') return data.name.toLocaleLowerCase(); return data.alerts?.length || 0; }

export function WatchlistSection({ watchlist, loading, metrics, onDeleteTicker, onAddInline, onUpdateAlert, onDeleteAlert, onToggleAlert, onAddTag, onRemoveTag, onUpdateMetadata }: Props) {
  const [sortField, setSortField] = useState<SortField>('symbol'); const [sortDirection, setSortDirection] = useState<SortDirection>('asc'); const [viewMode, setViewMode] = useState<ViewMode>('details'); const [filterTag, setFilterTag] = useState(''); const [query, setQuery] = useState('');
  const isCompact = useMediaQuery('(max-width: 760px)'); const effectiveViewMode: ViewMode = isCompact ? 'grid' : viewMode;
  const allTags = useMemo(() => { const names = new Set<string>(); Object.values(watchlist || {}).forEach((data) => data.tags?.forEach((tag) => names.add(tag.name))); return Array.from(names).sort((left, right) => left.localeCompare(right)); }, [watchlist]);
  const sortedWatchlist = useMemo<WatchlistEntry[]>(() => {
    const normalizedQuery = query.trim().toLocaleLowerCase();
    const entries = Object.entries(watchlist || {}).filter(([symbol, data]) => { const matchesTag = !filterTag || data.tags?.some((tag) => tag.name === filterTag); const matchesQuery = !normalizedQuery || symbol.toLocaleLowerCase().includes(normalizedQuery) || data.name.toLocaleLowerCase().includes(normalizedQuery); return matchesTag && matchesQuery; });
    return entries.sort((left, right) => { const leftValue = sortValue(left, sortField); const rightValue = sortValue(right, sortField); const comparison = typeof leftValue === 'number' && typeof rightValue === 'number' ? leftValue - rightValue : String(leftValue).localeCompare(String(rightValue)); return sortDirection === 'asc' ? comparison : -comparison; });
  }, [watchlist, filterTag, query, sortField, sortDirection]);
  const handleSort = (field: SortField) => { if (sortField === field) setSortDirection((current) => current === 'asc' ? 'desc' : 'asc'); else { setSortField(field); setSortDirection('asc'); } };
  const sortIndicator = (field: SortField) => sortField === field ? (sortDirection === 'asc' ? '↑' : '↓') : '';
  const totalCount = Object.keys(watchlist || {}).length; const hasFilters = Boolean(filterTag || query.trim());

  return (
    <section className="watchlist-section" aria-labelledby="watchlist-heading">
      <div className="section-heading watchlist-heading"><div><h2 id="watchlist-heading">Watchlist</h2><p>{totalCount === 1 ? '1 company' : `${totalCount} companies`} organised by alert rules and research status.</p></div></div>
      <div className="watchlist-toolbar">
        <label className="toolbar-search"><span>Filter companies</span><div className="input-with-icon"><Icon name="search" size={17} /><input type="search" placeholder="Ticker or company name" value={query} onChange={(event) => setQuery(event.target.value)} /></div></label>
        {allTags.length > 0 && <label className="toolbar-field"><span>Tag</span><select value={filterTag} onChange={(event) => setFilterTag(event.target.value)}><option value="">All tags</option>{allTags.map((tag) => <option key={tag} value={tag}>#{tag}</option>)}</select></label>}
        <label className="toolbar-field compact-only"><span>Sort by</span><select value={sortField} onChange={(event) => setSortField(event.target.value as SortField)}><option value="symbol">Ticker</option><option value="name">Company</option><option value="alerts">Alert count</option></select></label>
        <button className="icon-button compact-only" type="button" onClick={() => setSortDirection((current) => current === 'asc' ? 'desc' : 'asc')} aria-label={`Sort ${sortDirection === 'asc' ? 'descending' : 'ascending'}`} title={`Sort ${sortDirection === 'asc' ? 'descending' : 'ascending'}`}>{sortDirection === 'asc' ? '↑' : '↓'}</button>
        <div className="view-switch" aria-label="Watchlist view"><button type="button" className={viewMode === 'details' ? 'active' : ''} aria-pressed={viewMode === 'details'} onClick={() => setViewMode('details')}><Icon name="table" />Table</button><button type="button" className={viewMode === 'grid' ? 'active' : ''} aria-pressed={viewMode === 'grid'} onClick={() => setViewMode('grid')}><Icon name="grid" />Cards</button></div>
      </div>
      {loading ? <div className="loading-state" role="status">Loading watchlist…</div> : totalCount === 0 ? <div className="empty-state"><Icon name="watchlist" size={24} /><div><h3>Your watchlist is empty</h3><p>Create an alert above to add the first company.</p></div></div> : sortedWatchlist.length === 0 ? <div className="empty-state compact-empty"><div><h3>No companies match these filters</h3><p>Clear the search or tag filter to show the full watchlist.</p></div>{hasFilters && <button className="button button-secondary button-small" type="button" onClick={() => { setQuery(''); setFilterTag(''); }}>Clear filters</button>}</div> : effectiveViewMode === 'details' ? (
        <div className="table-container"><table className="details-table"><thead><tr>
          <th aria-sort={sortField === 'symbol' ? (sortDirection === 'asc' ? 'ascending' : 'descending') : 'none'}><button type="button" className="table-sort-button" onClick={() => handleSort('symbol')}>Ticker <span>{sortIndicator('symbol')}</span></button></th>
          <th aria-sort={sortField === 'name' ? (sortDirection === 'asc' ? 'ascending' : 'descending') : 'none'}><button type="button" className="table-sort-button" onClick={() => handleSort('name')}>Company <span>{sortIndicator('name')}</span></button></th>
          <th aria-sort={sortField === 'alerts' ? (sortDirection === 'asc' ? 'ascending' : 'descending') : 'none'}><button type="button" className="table-sort-button" onClick={() => handleSort('alerts')}>Alerts <span>{sortIndicator('alerts')}</span></button></th><th className="actions-column">Actions</th>
        </tr></thead><tbody>{sortedWatchlist.map(([symbol, data]) => <TickerRow key={symbol} symbol={symbol} data={data} metrics={metrics} onDeleteTicker={onDeleteTicker} onAddInline={onAddInline} onUpdateAlert={onUpdateAlert} onDeleteAlert={onDeleteAlert} onToggleAlert={onToggleAlert} onAddTag={onAddTag} onRemoveTag={onRemoveTag} onUpdateMetadata={onUpdateMetadata} />)}</tbody></table></div>
      ) : <div className="ticker-grid">{sortedWatchlist.map(([symbol, data]) => <TickerCard key={symbol} symbol={symbol} data={data} metrics={metrics} onDeleteTicker={onDeleteTicker} onAddInline={onAddInline} onUpdateAlert={onUpdateAlert} onDeleteAlert={onDeleteAlert} onToggleAlert={onToggleAlert} onAddTag={onAddTag} onRemoveTag={onRemoveTag} onUpdateMetadata={onUpdateMetadata} />)}</div>}
    </section>
  );
}
