import type { SecFundamentalsResponse } from '../types/secFacts';

interface Props {
  data: SecFundamentalsResponse | null;
  loading: boolean;
  error: string | null;
}

const METRIC_ORDER = [
  'revenue',
  'net_income',
  'total_assets',
  'total_liabilities',
  'stockholders_equity',
  'operating_cash_flow',
  'capex'
];

const METRIC_LABELS: Record<string, string> = {
  revenue: 'Revenue',
  net_income: 'Net income',
  total_assets: 'Assets',
  total_liabilities: 'Liabilities',
  stockholders_equity: 'Equity',
  operating_cash_flow: 'Operating cash flow',
  capex: 'Capex'
};

const compactNumber = new Intl.NumberFormat(undefined, {
  notation: 'compact',
  maximumFractionDigits: 1
});

function formatValue(value?: number | null, unit?: string | null) {
  if (value === null || value === undefined) {
    return 'Unavailable';
  }

  const formatted = compactNumber.format(value);
  return unit === 'USD' ? `$${formatted}` : `${formatted}${unit ? ` ${unit}` : ''}`;
}

function formatDate(value?: string | null) {
  if (!value) {
    return 'n/a';
  }
  return value;
}

export function AuditedSecFactsPanel({ data, loading, error }: Props) {
  const facts = [...(data?.facts || [])].sort(
    (left, right) => METRIC_ORDER.indexOf(left.metric) - METRIC_ORDER.indexOf(right.metric)
  );
  const firstError = data?.errors?.[0]?.message;

  return (
    <div className="sec-facts-panel">
      <div className="sec-facts-header">
        <div>
          <h5>Audited SEC Facts</h5>
          {data?.cik && <span>CIK {data.cik}</span>}
        </div>
        <span className="sec-facts-source">SEC EDGAR</span>
      </div>

      {loading ? (
        <p className="sec-facts-message">Loading SEC facts...</p>
      ) : error ? (
        <p className="sec-facts-message error">{error}</p>
      ) : data && facts.length > 0 ? (
        <div className="sec-facts-grid">
          {facts.map((fact) => (
            <div className="sec-fact" key={`${fact.metric}-${fact.accession || fact.concept}`}>
              <div className="sec-fact-main">
                <span>{METRIC_LABELS[fact.metric] || fact.metric}</span>
                <strong>{formatValue(fact.value, fact.unit)}</strong>
              </div>
              <div className="sec-fact-meta">
                <span>{fact.form || 'Filing'}</span>
                <span>Filed {formatDate(fact.filed_at)}</span>
                <span>As of {formatDate(fact.as_of_date)}</span>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="sec-facts-message">
          SEC audited facts are unavailable for this ticker. Non-US issuers or companies without a SEC ticker mapping may not appear in EDGAR company facts.
          {firstError ? ` ${firstError}` : ''}
        </p>
      )}
    </div>
  );
}
