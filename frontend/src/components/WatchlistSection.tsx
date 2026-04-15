import React from 'react';
import { Watchlist } from '../types/watchlist';
import { TickerCard } from './TickerCard';

interface Props {
  watchlist: Watchlist | null;
  loading: boolean;
  onDeleteTicker: (ticker: string) => void;
  onAddInline: (ticker: string, metric: string, operator: string, val: number) => void;
  onUpdateAlert: (ticker: string, metric: string, val: number) => void;
  onDeleteAlert: (ticker: string, metric: string) => void;
  onToggleAlert: (alertId: string, isActive: boolean) => void;
}

export function WatchlistSection({
  watchlist,
  loading,
  onDeleteTicker,
  onAddInline,
  onUpdateAlert,
  onDeleteAlert,
  onToggleAlert
}: Props) {
  return (
    <section className="watchlist-section">
      <h2>Watchlist</h2>
      {loading ? (
        <div className="loading">Loading data...</div>
      ) : (
        <div className="grid-container">
          {watchlist && Object.entries(watchlist).length > 0 ? (
            Object.entries(watchlist).map(([symbol, data]) => (
              <TickerCard
                key={symbol}
                symbol={symbol}
                data={data}
                onDeleteTicker={onDeleteTicker}
                onAddInline={onAddInline}
                onUpdateAlert={onUpdateAlert}
                onDeleteAlert={onDeleteAlert}
                onToggleAlert={onToggleAlert}
              />
            ))
          ) : (
            <p className="empty-message">No tickers in the watchlist.</p>
          )}
        </div>
      )}
    </section>
  );
}
