import type { MetricCatalogItem } from '../types/metrics';
import { getMetricLabel } from '../types/metrics';
import type { AiValuationResponse } from '../types/valuation';
import { Icon } from './Icon';

interface Props { valuation: AiValuationResponse | string; metrics: MetricCatalogItem[]; onClose: () => void; }
const labelText: Record<AiValuationResponse['valuation_label'], string> = { cheap: 'Potentially cheap', fair: 'Near fair value', expensive: 'Potentially expensive', inconclusive: 'Inconclusive' };

export function AiValuationPanel({ valuation, metrics, onClose }: Props) {
  if (typeof valuation === 'string') return <section className="research-brief-panel" aria-label="Assisted research brief"><div className="research-brief-header"><div><h5>Research brief</h5><span>Gemini-assisted</span></div><button className="icon-button" type="button" onClick={onClose} aria-label="Close research brief" title="Close"><Icon name="close" /></button></div><p>{valuation}</p></section>;
  return (
    <section className="research-brief-panel" aria-label="Assisted research brief">
      <div className="research-brief-header"><div><h5>Research brief</h5><span>Gemini-assisted · {valuation.data_quality} data quality</span></div><button className="icon-button" type="button" onClick={onClose} aria-label="Close research brief" title="Close"><Icon name="close" /></button></div>
      <div className="research-brief-verdict"><strong className={`valuation-label ${valuation.valuation_label}`}>{labelText[valuation.valuation_label]}</strong><p>{valuation.summary || valuation.analysis}</p></div>
      <div className="research-brief-columns"><ResearchList title="Key observations" items={valuation.key_observations} /><ResearchList title="Risks" items={valuation.risks} /><ResearchList title="Missing data" items={valuation.missing_data} /></div>
      {valuation.suggested_alerts.length > 0 && <div className="research-section suggested-alerts"><h6>Suggested alert ideas</h6><ul>{valuation.suggested_alerts.map((alert, index) => <li key={`${alert.metric}-${alert.operator}-${alert.value}-${index}`}><code>{getMetricLabel(metrics, alert.metric)} {alert.operator} {alert.value}</code><span>{alert.rationale}</span></li>)}</ul></div>}
      <p className="research-disclaimer">{valuation.disclaimer}</p>
    </section>
  );
}
function ResearchList({ title, items }: { title: string; items: string[] }) { if (items.length === 0) return null; return <div className="research-section"><h6>{title}</h6><ul>{items.map((item) => <li key={item}>{item}</li>)}</ul></div>; }
