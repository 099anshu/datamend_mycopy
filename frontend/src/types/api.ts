import {
  Severity,
  MissingValueStrategy,
  CorruptionMethod,
  CorruptionConfig,
  MissingValueHandlingConfig,
  AnalysisRequestPayload,
  TimestampScore,
  ScoresResponse,
  AnomalyItem,
  AnalysisJobResponse,
  AnalysisDetailResponse,
} from '../features/analysis/services/schemas';

export type {
  Severity,
  MissingValueStrategy,
  CorruptionMethod,
  CorruptionConfig,
  MissingValueHandlingConfig,
  AnalysisRequestPayload,
  TimestampScore,
  ScoresResponse,
  AnomalyItem,
  AnalysisJobResponse,
  AnalysisDetailResponse,
};

export type DashboardStatus =
  | 'idle'
  | 'loading_scores'
  | 'scores_ready'
  | 'analyzing'
  | 'completed'
  | 'error';
