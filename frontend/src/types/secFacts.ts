export interface SecFact {
  metric: string;
  value?: number | null;
  unit?: string | null;
  concept?: string | null;
  label?: string | null;
  fiscal_year?: number | null;
  fiscal_period?: string | null;
  form?: string | null;
  as_of_date?: string | null;
  filed_at?: string | null;
  accession?: string | null;
  source: 'sec' | string;
}

export interface SecFactError {
  metric?: string | null;
  message: string;
}

export interface SecFundamentalsResponse {
  ticker: string;
  cik?: string | null;
  company_name?: string | null;
  facts: SecFact[];
  errors: SecFactError[];
}
