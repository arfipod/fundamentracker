import { useCallback, useEffect, useState } from 'react';
import { apiFetch } from '../lib/apiClient';
import { Icon } from './Icon';
import type { Signal } from '../types/signals';

interface SignalInboxProps { refreshToken: number; }
function formatCreatedAt(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}
function severityLabel(value?: string | null) { if (value === 'critical') return 'Priority'; if (value === 'warning') return 'Review'; return 'Info'; }

export function SignalInbox({ refreshToken }: SignalInboxProps) {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [updatingId, setUpdatingId] = useState<string | null>(null);

  const fetchSignals = useCallback(async () => {
    try {
      setLoading(true);
      const response = await apiFetch('/signals?status=open&limit=50');
      if (!response.ok) throw new Error('Signals could not be loaded.');
      setSignals(await response.json()); setError(null);
    } catch (signalError) { setError(signalError instanceof Error ? signalError.message : 'Signals could not be loaded.'); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { void fetchSignals(); }, [fetchSignals, refreshToken]);

  const updateSignal = async (signalId: string, action: 'acknowledge' | 'dismiss') => {
    try {
      setUpdatingId(signalId);
      const response = await apiFetch(`/signals/${signalId}/${action}`, { method: 'PATCH' });
      if (!response.ok) throw new Error(action === 'acknowledge' ? 'The signal could not be marked as reviewed.' : 'The signal could not be dismissed.');
      await fetchSignals();
    } catch (signalError) { setError(signalError instanceof Error ? signalError.message : 'The signal could not be updated.'); }
    finally { setUpdatingId(null); }
  };

  return (
    <section className="signal-inbox" aria-labelledby="signals-heading">
      <div className="section-heading"><div><h2 id="signals-heading">Signals</h2><p>Alert events that are waiting for a research decision.</p></div><div className="section-actions">{signals.length > 0 && <span className="section-count">{signals.length} open</span>}<button className="button button-secondary button-small" type="button" onClick={fetchSignals} disabled={loading}><Icon name="refresh" />Refresh</button></div></div>
      {error && <div className="notice notice-error" role="alert">{error}</div>}
      {loading && signals.length === 0 ? <div className="loading-state" role="status">Loading signals…</div> : signals.length === 0 ? (
        <div className="empty-state"><Icon name="signals" size={24} /><div><h3>No signals need review</h3><p>Run a scan to check the current values against your alert rules.</p></div><button className="button button-secondary button-small" type="button" onClick={fetchSignals}>Check again</button></div>
      ) : (
        <ul className="signal-list">{signals.map((signal) => <li key={signal.id}><article className={`signal-item severity-${signal.severity || 'info'}`}><div className="signal-indicator" aria-hidden="true" /><div className="signal-main"><div className="signal-meta">{signal.ticker_symbol && <strong className="signal-ticker">{signal.ticker_symbol}</strong>}<span>{severityLabel(signal.severity)}</span><time dateTime={signal.created_at}>{formatCreatedAt(signal.created_at)}</time></div><h3>{signal.title}</h3>{signal.message && <p>{signal.message}</p>}</div><div className="signal-actions"><button className="button button-secondary button-small" type="button" disabled={updatingId === signal.id} onClick={() => updateSignal(signal.id, 'acknowledge')}><Icon name="check" />Mark reviewed</button><button className="button button-quiet button-small danger-text" type="button" disabled={updatingId === signal.id} onClick={() => updateSignal(signal.id, 'dismiss')}>Dismiss</button></div></article></li>)}</ul>
      )}
    </section>
  );
}
