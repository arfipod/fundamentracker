import { useState, useCallback } from 'react';
import type { Watchlist } from '../types/watchlist';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export function useWatchlist() {
  const [watchlist, setWatchlist] = useState<Watchlist | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [undoQueue, setUndoQueue] = useState<{ ticker: string, name: string, alerts: any[], id: number } | null>(null);

  const fetchWatchlist = useCallback(async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_URL}/watchlist`);
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

  const handleAddAlertInline = async (tickerToAdd: string, metricToAdd: string, operatorToAdd: string, targetValueToAdd: number) => {
    if (watchlist && watchlist[tickerToAdd]) {
      const hasMetric = watchlist[tickerToAdd].alerts.some(a => a.metric === metricToAdd);
      if (hasMetric) {
        if (!window.confirm("Ya tienes esta métrica configurada para esta empresa. ¿Deseas agregarla de todas formas?")) {
          return false;
        }
      }
    }

    try {
      const response = await fetch(`${API_URL}/add`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ticker: tickerToAdd,
          metric: metricToAdd,
          operator: operatorToAdd,
          value: targetValueToAdd,
          alert_type: "absolute"
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

  const handleUpdateTarget = async (tickerToUpdate: string, metricToUpdate: string, newValue: number) => {
    try {
      const response = await fetch(`${API_URL}/update`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ticker: tickerToUpdate,
          metric: metricToUpdate,
          value: newValue,
        }),
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

  const handleDeleteAlert = async (tickerToDelete: string, metricToDelete: string) => {
    try {
      let alertToUndo = null;
      if (watchlist && watchlist[tickerToDelete]) {
        alertToUndo = watchlist[tickerToDelete].alerts.find(a => a.metric === metricToDelete);
      }
      
      const response = await fetch(`${API_URL}/remove/${tickerToDelete}/${metricToDelete}`, {
        method: 'DELETE',
      });
      if (!response.ok) throw new Error('Error removing the alert');
      
      if (alertToUndo) {
        const id = Date.now();
        setUndoQueue({ ticker: tickerToDelete, name: watchlist![tickerToDelete].name, alerts: [alertToUndo], id });
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
      let alertsToUndo: any[] = [];
      let nameToUndo = "";
      if (watchlist && watchlist[tickerToDelete]) {
        alertsToUndo = watchlist[tickerToDelete].alerts;
        nameToUndo = watchlist[tickerToDelete].name;
      }

      const response = await fetch(`${API_URL}/remove/${tickerToDelete}`, {
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
      const response = await fetch(`${API_URL}/alerts/${alertId}/toggle`, {
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
      await fetch(`${API_URL}/add`, {
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
