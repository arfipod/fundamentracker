import { useState, useCallback } from 'react';
import { apiFetch } from '../lib/apiClient';
import type { Alert, Watchlist, WatchlistMetadata } from '../types/watchlist';

type UndoQueue = { ticker: string, alerts: Alert[], id: number };

export function useWatchlist() {
  const [watchlist, setWatchlist] = useState<Watchlist | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [undoQueue, setUndoQueue] = useState<UndoQueue | null>(null);

  const fetchWatchlist = useCallback(async () => {
    try {
      setLoading(true);
      const response = await apiFetch('/watchlist');
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
  }, []);

  const handleAddAlertInline = async (tickerToAdd: string, metricToAdd: string, operatorToAdd: string, targetValueToAdd: number, alertType: string = 'absolute') => {
    if (watchlist && watchlist[tickerToAdd]) {
      const hasMetric = watchlist[tickerToAdd].alerts.some(a => a.metric === metricToAdd);
      if (hasMetric) {
        if (!window.confirm("Ya tienes esta métrica configurada para esta empresa. ¿Deseas agregarla de todas formas?")) {
          return false;
        }
      }
    }

    try {
      const response = await apiFetch('/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ticker: tickerToAdd,
          metric: metricToAdd,
          operator: operatorToAdd,
          value: targetValueToAdd,
          alert_type: alertType
        }),
      });
      if (!response.ok) throw new Error('Error adding the alert');
      await fetchWatchlist();
      return true;
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      }
      return false;
    }
  };

  const handleUpdateTarget = async (alertId: string, newValue: number) => {
    try {
      const response = await apiFetch(`/alerts/${alertId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ value: newValue }),
      });
      if (!response.ok) throw new Error('Error updating alert');
      await fetchWatchlist();
      return true;
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      }
      return false;
    }
  };

  const handleDeleteAlert = async (alertId: string, tickerToDelete: string) => {
    try {
      let alertToUndo: Alert | undefined;
      if (watchlist && watchlist[tickerToDelete]) {
        alertToUndo = watchlist[tickerToDelete].alerts.find(a => a.id === alertId);
      }
      if (!alertToUndo && watchlist) {
        for (const [symbol, data] of Object.entries(watchlist)) {
          const alert = data.alerts.find(a => a.id === alertId);
          if (alert) {
            tickerToDelete = symbol;
            alertToUndo = alert;
            break;
          }
        }
      }
      
      const response = await apiFetch(`/alerts/${alertId}`, {
        method: 'DELETE',
      });
      if (!response.ok) throw new Error('Error removing the alert');
      
      if (alertToUndo) {
        const id = Date.now();
        setUndoQueue({ ticker: tickerToDelete, alerts: [alertToUndo], id });
        setTimeout(() => setUndoQueue(prev => prev?.id === id ? null : prev), 6000);
      }
      
      await fetchWatchlist();
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      }
    }
  };

  const handleDelete = async (tickerToDelete: string) => {
    try {
      const response = await apiFetch(`/remove/${tickerToDelete}`, {
        method: 'DELETE',
      });
      if (!response.ok) throw new Error('Error removing the ticker');
      setUndoQueue(null);
      
      await fetchWatchlist();
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      }
    }
  };

  const handleToggleAlert = async (alertId: string, isActive: boolean) => {
    try {
      const response = await apiFetch(`/alerts/${alertId}/toggle`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_active: isActive }),
      });
      if (!response.ok) throw new Error('Error toggling alert');
      await fetchWatchlist();
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      }
    }
  };

  const handleAddTag = async (ticker: string, name: string) => {
    try {
      const response = await apiFetch(`/watchlist/${ticker}/tags`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name }),
      });
      if (!response.ok) throw new Error('Error adding tag');
      await fetchWatchlist();
      return true;
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      }
      return false;
    }
  };

  const handleRemoveTag = async (ticker: string, tagNameOrId: string) => {
    try {
      const response = await apiFetch(`/watchlist/${ticker}/tags/${encodeURIComponent(tagNameOrId)}`, {
        method: 'DELETE',
      });
      if (!response.ok) throw new Error('Error removing tag');
      await fetchWatchlist();
      return true;
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      }
      return false;
    }
  };

  const handleUpdateMetadata = async (ticker: string, metadata: Partial<WatchlistMetadata>) => {
    try {
      const response = await apiFetch(`/watchlist/${ticker}/metadata`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(metadata),
      });
      if (!response.ok) throw new Error('Error updating metadata');
      await fetchWatchlist();
      return true;
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      }
      return false;
    }
  };

  const handleUndo = async () => {
    if (!undoQueue) return;
    
    try {
      for (const alert of undoQueue.alerts) {
        const response = await apiFetch(`/alerts/${alert.id}/restore`, {
          method: 'POST',
        });
        if (!response.ok) {
          throw new Error('Error restoring the alert');
        }
      }
      setUndoQueue(null);
      await fetchWatchlist();
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      }
    }
  };

  return {
    watchlist,
    loading,
    error,
    setError,
    fetchWatchlist,
    handleAddAlertInline,
    handleUpdateTarget,
    handleDeleteAlert,
    handleDelete,
    handleToggleAlert,
    handleAddTag,
    handleRemoveTag,
    handleUpdateMetadata,
    undoQueue,
    handleUndo
  };
}
