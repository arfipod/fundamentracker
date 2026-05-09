import type { DataQualityMetadata } from '../types/watchlist';

interface DataQualityBadgeProps {
  metadata: DataQualityMetadata;
}

function formatDateTime(value?: string | null) {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function formatDate(value?: string | null) {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

function formatConfidence(value?: number | null) {
  if (value === undefined || value === null) return null;
  if (value <= 1) return `${Math.round(value * 100)}%`;
  return `${Math.round(value)}%`;
}

export function DataQualityBadge({ metadata }: DataQualityBadgeProps) {
  const source = metadata.source || 'unknown';
  const confidence = formatConfidence(metadata.confidence);
  const titleParts = [
    `Source: ${source}`,
    metadata.stale ? 'Stale: yes' : 'Stale: no',
    metadata.fetched_at ? `Fetched: ${formatDateTime(metadata.fetched_at)}` : null,
    metadata.as_of_date ? `As of: ${formatDate(metadata.as_of_date)}` : null,
    metadata.expires_at ? `Expires: ${formatDateTime(metadata.expires_at)}` : null,
    confidence ? `Confidence: ${confidence}` : null,
  ].filter(Boolean);

  return (
    <span
      className={`data-quality-badge${metadata.stale ? ' stale' : ''}`}
      title={titleParts.join('\n')}
      aria-label={titleParts.join(', ')}
    >
      <span className="data-quality-source">{source}</span>
      {metadata.stale && <span className="data-quality-stale">Stale</span>}
      {confidence && <span className="data-quality-confidence">{confidence}</span>}
    </span>
  );
}
