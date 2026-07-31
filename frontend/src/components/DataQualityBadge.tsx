import type { DataQualityMetadata } from '../types/watchlist';

interface DataQualityBadgeProps { metadata: DataQualityMetadata; }
function formatDateTime(value?: string | null) { if (!value) return null; const date = new Date(value); if (Number.isNaN(date.getTime())) return value; return date.toLocaleString(undefined, { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }); }
function formatDate(value?: string | null) { if (!value) return null; const date = new Date(value); if (Number.isNaN(date.getTime())) return value; return date.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' }); }
function formatConfidence(value?: number | null) { if (value === undefined || value === null) return null; return `${Math.round(value <= 1 ? value * 100 : value)}%`; }
function sourceLabel(value?: string | null) { if (!value) return 'Unknown source'; return value.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase()); }

export function DataQualityBadge({ metadata }: DataQualityBadgeProps) {
  const source = sourceLabel(metadata.source);
  const confidence = formatConfidence(metadata.confidence);
  const titleParts = [`Source: ${source}`, metadata.stale ? 'Freshness: stale' : 'Freshness: current', metadata.fetched_at ? `Fetched: ${formatDateTime(metadata.fetched_at)}` : null, metadata.as_of_date ? `As of: ${formatDate(metadata.as_of_date)}` : null, metadata.expires_at ? `Expires: ${formatDateTime(metadata.expires_at)}` : null, confidence ? `Confidence: ${confidence}` : null].filter(Boolean);
  return <span className={`data-quality${metadata.stale ? ' stale' : ''}`} title={titleParts.join('\n')} aria-label={titleParts.join(', ')}><span className="data-quality-dot" aria-hidden="true" /><span>{source}</span>{metadata.stale && <strong>Stale</strong>}{confidence && <span>{confidence}</span>}</span>;
}
