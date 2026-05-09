export interface SuggestedAlert {
  metric: string;
  operator: string;
  value: number;
  rationale: string;
}

export interface ValuationSource {
  metric: string;
  source: string | null;
  as_of_date: string | null;
  fetched_at: string | null;
  stale: boolean | null;
}

export interface AiValuationResponse {
  ticker: string;
  company_name: string | null;
  summary: string;
  valuation_label: 'cheap' | 'fair' | 'expensive' | 'inconclusive';
  data_quality: 'high' | 'medium' | 'low';
  key_observations: string[];
  risks: string[];
  missing_data: string[];
  suggested_alerts: SuggestedAlert[];
  sources: ValuationSource[];
  disclaimer: string;
  analysis?: string;
}
