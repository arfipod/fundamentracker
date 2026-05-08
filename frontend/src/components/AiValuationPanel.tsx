import type { MetricCatalogItem } from '../types/metrics';
import { getMetricLabel } from '../types/metrics';
import type { AiValuationResponse } from '../types/valuation';

interface Props {
  valuation: AiValuationResponse | string;
  metrics: MetricCatalogItem[];
  onClose: () => void;
}

const labelText: Record<AiValuationResponse['valuation_label'], string> = {
  cheap: 'Cheap',
  fair: 'Fair',
  expensive: 'Expensive',
  inconclusive: 'Inconclusive',
};

export function AiValuationPanel({ valuation, metrics, onClose }: Props) {
  if (typeof valuation === 'string') {
    return (
      <div className="ai-valuation-panel">
        <button className="ai-valuation-close" onClick={onClose} type="button" aria-label="Close AI analysis">x</button>
        <h5>Gemini AI Analysis</h5>
        <p className="ai-valuation-text">{valuation}</p>
      </div>
    );
  }

  return (
    <div className="ai-valuation-panel">
      <button className="ai-valuation-close" onClick={onClose} type="button" aria-label="Close AI analysis">x</button>
      <div className="ai-valuation-header">
        <h5>Gemini AI Analysis</h5>
        <span className={`ai-valuation-label ${valuation.valuation_label}`}>
          {labelText[valuation.valuation_label]}
        </span>
        <span className="ai-valuation-quality">{valuation.data_quality} data</span>
      </div>

      <p className="ai-valuation-summary">{valuation.summary || valuation.analysis}</p>

      <AiList title="Key observations" items={valuation.key_observations} />
      <AiList title="Risks" items={valuation.risks} />
      <AiList title="Missing data" items={valuation.missing_data} />

      {valuation.suggested_alerts.length > 0 && (
        <div className="ai-valuation-section">
          <h6>Suggested alerts</h6>
          <ul className="ai-suggested-alerts">
            {valuation.suggested_alerts.map((alert, index) => (
              <li key={`${alert.metric}-${alert.operator}-${alert.value}-${index}`}>
                <code>
                  {getMetricLabel(metrics, alert.metric)} {alert.operator} {alert.value}
                </code>
                <span>{alert.rationale}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <p className="ai-valuation-disclaimer">{valuation.disclaimer}</p>
    </div>
  );
}

function AiList({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) {
    return null;
  }

  return (
    <div className="ai-valuation-section">
      <h6>{title}</h6>
      <ul>
        {items.map(item => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}
