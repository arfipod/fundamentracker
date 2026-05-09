import { useCallback, useState } from 'react';
import { apiFetch } from '../lib/apiClient';
import type { SecFundamentalsResponse } from '../types/secFacts';

export function useSecFacts(symbol: string) {
  const [data, setData] = useState<SecFundamentalsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (data || loading) {
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const response = await apiFetch(`/fundamentals/sec/${encodeURIComponent(symbol)}`);
      if (!response.ok) {
        const payload = await response.json().catch(() => null);
        throw new Error(payload?.detail || 'Failed to load SEC facts');
      }
      setData(await response.json());
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Failed to load SEC facts');
    } finally {
      setLoading(false);
    }
  }, [data, loading, symbol]);

  return { data, loading, error, load };
}
