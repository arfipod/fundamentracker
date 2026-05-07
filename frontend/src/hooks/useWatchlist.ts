import { useState, useCallback } from 'react';
import { apiFetch } from '../lib/apiClient';
import type { Alert, Watchlist } from '../types/watchlist';

type UndoQueue = { ticker: string, name: string, alerts: Alert[], id: number };

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
        const name = watchlist?.[tickerToDelete]?.name || tickerToDelete;
        setUndoQueue({ ticker: tickerToDelete, name, alerts: [alertToUndo], id });
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
      let alertsToUndo: Alert[] = [];
      let nameToUndo = "";
      if (watchlist && watchlist[tickerToDelete]) {
        alertsToUndo = watchlist[tickerToDelete].alerts;
        nameToUndo = watchlist[tickerToDelete].name;
      }

      const response = await apiFetch(`/remove/${tickerToDelete}`, {
        method: 'DELETE',
      });
      if (!response.ok) throw new Error('Error removing the ticker');
      
      if (alertsToUndo.length >= 0) {
        const id = Date.now();
        setUndoQueue({ ticker: tickerToDelete, name: nameToUndo, alerts: alertsToUndo, id });
        setTimeout(() => setUndoQueue(prev => prev?.id === id ? null : prev), 6000);
      }
      
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

  const handleUndo = async () => {
    if (!undoQueue) return;
    
    // Add ticker and alerts back
    for (const alert of undoQueue.alerts) {
      await apiFetch('/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ticker: undoQueue.ticker,
          metric: alert.metric,
          operator: alert.operator,
          value: alert.target,
          alert_type: alert.alert_type
        }),
      });
    }
    setUndoQueue(null);
    await fetchWatchlist();
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
    undoQueue,
    handleUndo
  };
}
