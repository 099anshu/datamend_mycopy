import { z } from 'zod';

export const SeveritySchema = z.enum(['HIGH', 'MEDIUM', 'LOW']);
export type Severity = z.infer<typeof SeveritySchema>;

export const MissingValueStrategySchema = z.enum([
  'reject',
  'ffill',
  'bfill',
  'mean',
  'interpolate',
]);
export type MissingValueStrategy = z.infer<typeof MissingValueStrategySchema>;

export const CorruptionMethodSchema = z.enum([
  'mcar',
  'mar_logistic',
  'mnar_x',
  'mnar_t',
  'mnar_nonuniform',
  'rdo',
  'seq_missing',
  'block_missing',
]);
export type CorruptionMethod = z.infer<typeof CorruptionMethodSchema>;

export const CorruptionConfigSchema = z.object({
  enabled: z.boolean(),
  method: CorruptionMethodSchema,
  params: z.record(z.string(), z.number()),
});
export type CorruptionConfig = z.infer<typeof CorruptionConfigSchema>;

export const MissingValueHandlingConfigSchema = z.object({
  strategy: MissingValueStrategySchema,
});
export type MissingValueHandlingConfig = z.infer<typeof MissingValueHandlingConfigSchema>;

export const AnalysisRequestPayloadSchema = z.object({
  analysisId: z.string(),
  datasetName: z.string(),
  columns: z.array(z.string()),
  detector: z.string(),
  threshold: z.number(),
  corruption: CorruptionConfigSchema.nullable(),
  missingValueHandling: MissingValueHandlingConfigSchema,
});
export type AnalysisRequestPayload = z.infer<typeof AnalysisRequestPayloadSchema>;

export const TimestampScoreSchema = z.object({
  timestamp: z.string(),
  values: z.record(z.string(), z.number()),
  score: z.number(),
  severity: SeveritySchema,
});
export type TimestampScore = z.infer<typeof TimestampScoreSchema>;

export const ScoresResponseSchema = z.object({
  analysisId: z.string(),
  status: z.string(),
  detector: z.string(),
  scores: z.array(TimestampScoreSchema),
  missingRate: z.number().optional(),
  missingValueHandling: z.string().optional(),
});
export type ScoresResponse = z.infer<typeof ScoresResponseSchema>;

export const AnomalyItemSchema = z.object({
  id: z.string().optional(),
  analysisId: z.string().optional(),
  timestamp: z.string(),
  columnName: z.string().optional(),
  column: z.string().optional(),
  value: z.number().optional(),
  score: z.number().optional(),
  severity: SeveritySchema,
});
export type AnomalyItem = z.infer<typeof AnomalyItemSchema>;

export const AnalysisJobResponseSchema = z.object({
  analysisId: z.string(),
  status: z.enum(['RUNNING', 'COMPLETED', 'FAILED']),
});
export type AnalysisJobResponse = z.infer<typeof AnalysisJobResponseSchema>;

export const AnalysisDetailResponseSchema = z.object({
  id: z.string(),
  datasetId: z.string(),
  status: z.enum(['RUNNING', 'COMPLETED', 'FAILED']),
  detector: z.string(),
  startedAt: z.string().optional(),
  completedAt: z.string().optional(),
  anomalies: z.array(AnomalyItemSchema),
});
export type AnalysisDetailResponse = z.infer<typeof AnalysisDetailResponseSchema>;
