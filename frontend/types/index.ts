export type Intent =
  | "FACTUAL_SCHEME"
  | "FACTUAL_OPERATIONAL"
  | "FACTUAL_REGULATORY"
  | "FACTUAL_GROWW"
  | "HISTORICAL_PERFORMANCE"
  | "ADVICE"
  | "PERFORMANCE_PREDICTION"
  | "PERFORMANCE_COMPARISON"
  | "MARKET_TIMING"
  | "PII_ACCOUNT"
  | "OUT_OF_SCOPE"
  | "AMBIGUOUS";

export interface SourceInfo {
  title: string | null;
  url: string | null;
  page: number | null;
  source_id: string | null;
}

export interface ChatResponse {
  answer: string;
  intent: Intent;
  scheme: string | null;
  topic?: string | null;
  source: SourceInfo | null;
  last_updated: string | null;
  refused: boolean;
  refusal_type?: string | null;
}
