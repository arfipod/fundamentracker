import { useCallback, useEffect, useState } from 'react';
import { apiFetch } from '../lib/apiClient';
import type { Signal } from '../types/signals';

interface SignalInboxProps {
  refreshToken: number;
}

function formatCreatedAt(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

export function SignalInbox({ refreshToken }: SignalInboxProps) {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [updatingId, setUpdatingId] = useState<string | null>(null);

  const fetchSignals = useCallback(async () => {
    try {
      setLoading(true);
      const response = await apiFetch('/signals?status=open&limit=50');
      if (!response.ok) {
        throw new Error('Failed to load signals');
      }
      const data = await response.json();
      setSignals(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load signals');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSignals();
  }, [fetchSignals, refreshToken]);

  const updateSignal = async (signalId: string, action: 'acknowledge' | 'dismiss') => {
    try {
      setUpdatingId(signalId);
      const response = await apiFetch(`/signals/${signalId}/${action}`, { method: 'PATCH' });
      if (!response.ok) {
        throw new Error(`Failed to ${action} signal`);
      }
      await fetchSignals();
    } catch (err) {
      setError(err instanceof Error ? err.message : `Failed to ${action} signal`);
    } finally {
      setUpdatingId(null);
    }
  };

  return (
    <section className="signal-inbox">
      <div className="section-header">
        <div>
          <h2>Signals</h2>
          <p className="section-subtitle">Open investor events from scans and alerts</p>
        </div>
        <button className="btn-secondary" onClick={fetchSignals} disabled={loading}>
          Refresh
        </button>
      </div>

      {error && <div className="error-message">{error}</div>}

      {loading && signals.length === 0 ? (
        <div className="empty-state">Loading signals...</div>
      ) : signals.length === 0 ? (
        <div className="empty-state">No open signals.</div>
      ) : (
        <div className="signal-list">
          {signals.map((signal) => (
            <article className={`signal-item severity-${signal.severity || 'info'}`} key={signal.id}>
              <div className="signal-main">
                <div className="signal-meta">
                  {signal.ticker_symbol && <span className="signal-ticker">{signal.ticker_symbol}</span>}
                  <span className="signal-severity">{signal.severity || 'info'}</span>
                  <span>{formatCreatedAt(signal.created_at)}</span>
                </div>
                <h3>{signal.title}</h3>
                {signal.message && <p>{signal.message}</p>}
              </div>
              <div className="signal-actions">
                <button
                  className="btn-secondary"
                  disabled={updatingId === signal.id}
                  onClick={() => updateSignal(signal.id, 'acknowledge')}
                >
                  Acknowledge
                </button>
                <button
                  className="btn-danger-text"
                  disabled={updatingId === signal.id}
                  onClick={() => updateSignal(signal.id, 'dismiss')}
                >
                  Dismiss
                </button>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
