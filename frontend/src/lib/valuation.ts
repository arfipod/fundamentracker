import type { AiValuationResponse } from '../types/valuation';

export function parseAiValuationResponse(payload: unknown): AiValuationResponse | string {
  if (isAiValuationResponse(payload)) {
    return payload;
  }

  if (isRecord(payload) && typeof payload.analysis === 'string') {
    return payload.analysis;
  }

  return 'AI valuation response was not in a recognized format.';
}

function isAiValuationResponse(payload: unknown): payload is AiValuationResponse {
  return (
    isRecord(payload) &&
    typeof payload.ticker === 'string' &&
    typeof payload.summary === 'string' &&
    typeof payload.valuation_label === 'string' &&
    Array.isArray(payload.key_observations) &&
    Array.isArray(payload.risks) &&
    Array.isArray(payload.missing_data) &&
    Array.isArray(payload.suggested_alerts) &&
    typeof payload.disclaimer === 'string'
  );
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}
