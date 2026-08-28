import { z } from 'zod';

export const DatasetSourceSchema = z.enum(['tsdb', 'upload']);
export type DatasetSource = z.infer<typeof DatasetSourceSchema>;

export const ColumnKindSchema = z.enum(['numeric', 'datetime', 'categorical']);
export type ColumnKind = z.infer<typeof ColumnKindSchema>;

export const ColumnProfileSchema = z.object({
  name: z.string(),
  kind: ColumnKindSchema,
  dtype: z.string(),
  nullCount: z.number(),
  nullRate: z.number(),
  min: z.number().nullable().optional(),
  max: z.number().nullable().optional(),
  mean: z.number().nullable().optional(),
  std: z.number().nullable().optional(),
  sampleValues: z.array(z.string()).default([]),
});
export type ColumnProfile = z.infer<typeof ColumnProfileSchema>;

export const DatasetProfileSchema = z.object({
  rowCount: z.number(),
  columnCount: z.number(),
  timestampColumn: z.string().nullable().optional(),
  signalColumns: z.array(z.string()).default([]),
  columns: z.array(ColumnProfileSchema).default([]),
  preview: z.array(z.record(z.string(), z.unknown())).default([]),
});
export type DatasetProfile = z.infer<typeof DatasetProfileSchema>;

export const UploadedDatasetSchema = z.object({
  datasetId: z.string(),
  name: z.string(),
  source: DatasetSourceSchema.default('upload'),
  uploadedAt: z.string(),
  profile: DatasetProfileSchema,
});
export type UploadedDataset = z.infer<typeof UploadedDatasetSchema>;

export const UploadedDatasetSummarySchema = z.object({
  datasetId: z.string(),
  name: z.string(),
  source: DatasetSourceSchema.default('upload'),
  uploadedAt: z.string(),
  rowCount: z.number(),
  columnCount: z.number(),
});
export type UploadedDatasetSummary = z.infer<typeof UploadedDatasetSummarySchema>;
