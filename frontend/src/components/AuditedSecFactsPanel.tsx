import type { SecFundamentalsResponse } from '../types/secFacts';
import { Icon } from './Icon';

interface Props { data: SecFundamentalsResponse | null; loading: boolean; error: string | null; }
const METRIC_ORDER = ['revenue', 'net_income', 'total_assets', 'total_liabilities', 'stockholders_equity', 'operating_cash_flow', 'capex'];
const METRIC_LABELS: Record<string, string> = { revenue: 'Revenue', net_income: 'Net income', total_assets: 'Assets', total_liabilities: 'Liabilities', stockholders_equity: 'Equity', operating_cash_flow: 'Operating cash flow', capex: 'Capital expenditure' };
const compactNumber = new Intl.NumberFormat(undefined, { notation: 'compact', maximumFractionDigits: 1 });
function formatValue(value?: number | null, unit?: string | null) { if (value === null || value === undefined) return 'Unavailable'; const formatted = compactNumber.format(value); return unit === 'USD' ? `$${formatted}` : `${formatted}${unit ? ` ${unit}` : ''}`; }

export function AuditedSecFactsPanel({ data, loading, error }: Props) {
  const facts = [...(data?.facts || [])].sort((left, right) => METRIC_ORDER.indexOf(left.metric) - METRIC_ORDER.indexOf(right.metric));
  const firstError = data?.errors?.[0]?.message;
  return (
    <section className="sec-facts-panel" aria-label="Audited SEC facts">
      <div className="sec-facts-header"><div><h5><Icon name="database" />Audited SEC facts</h5><span>{data?.cik ? `CIK ${data.cik}` : 'SEC EDGAR company facts'}</span></div><span className="source-label">SEC EDGAR</span></div>
      {loading ? <p className="panel-message">Loading SEC facts…</p> : error ? <p className="panel-message error" role="alert">{error}</p> : data && facts.length > 0 ? <dl className="sec-facts-list">{facts.map((fact) => <div className="sec-fact-row" key={`${fact.metric}-${fact.accession || fact.concept}`}><dt><strong>{METRIC_LABELS[fact.metric] || fact.metric}</strong><span>{fact.form || 'Filing'} · filed {fact.filed_at || 'n/a'} · as of {fact.as_of_date || 'n/a'}</span></dt><dd>{formatValue(fact.value, fact.unit)}</dd></div>)}</dl> : <p className="panel-message">Audited company facts are not available for this ticker. Non-US issuers and companies without a SEC ticker mapping may not appear in EDGAR.{firstError ? ` ${firstError}` : ''}</p>}
    </section>
  );
}
