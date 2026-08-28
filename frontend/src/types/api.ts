export type Severity = 'HIGH' | 'MEDIUM' | 'LOW';

export type MissingValueStrategy = 'reject' | 'ffill' | 'bfill' | 'mean' | 'interpolate';

export type CorruptionMethod =
  | 'mcar'
  | 'mar_logistic'
  | 'mnar_x'
  | 'mnar_t'
  | 'mnar_nonuniform'
  | 'rdo'
  | 'seq_missing'
  | 'block_missing';

export interface CorruptionConfig {
  enabled: boolean;
  method: CorruptionMethod;
  params: Record<string, number>;
}

export interface MissingValueHandlingConfig {
  strategy: MissingValueStrategy;
}

export interface AnalysisRequestPayload {
  analysisId: string;
  datasetName: string;
  columns: string[];
  detector: string;
  threshold: number;
  corruption: CorruptionConfig | null;
  missingValueHandling: MissingValueHandlingConfig;
}

export interface TimestampScore {
  timestamp: string;
  values: Record<string, number>;
  score: number;
  severity: Severity;
}

export interface ScoresResponse {
  analysisId: string;
  status: string;
  detector: string;
  scores: TimestampScore[];
  missingRate?: number;
  missingValueHandling?: string;
}

export interface AnomalyItem {
  id?: string;
  analysisId?: string;
  timestamp: string;
  columnName: string;
  column?: string;
  value?: number;
  score?: number;
  severity: Severity;
}

export interface AnalysisJobResponse {
  analysisId: string;
  status: 'RUNNING' | 'COMPLETED' | 'FAILED';
}

export interface AnalysisDetailResponse {
  id: string;
  datasetId: string;
  status: 'RUNNING' | 'COMPLETED' | 'FAILED';
  detector: string;
  startedAt?: string;
  completedAt?: string;
  anomalies: AnomalyItem[];
}

export type DashboardStatus =
  | 'idle'
  | 'loading_scores'
  | 'scores_ready'
  | 'analyzing'
  | 'completed'
  | 'error';
