import { CorruptionMethod } from '@/types/api';

export const CORRUPTION_PARAM_CONFIGS: Record<
  CorruptionMethod,
  { name: string; default: number; step: number; min?: number; max?: number }[]
> = {
  mcar: [{ name: 'p', default: 0.1, step: 0.05, min: 0.01, max: 0.99 }],
  rdo: [{ name: 'p', default: 0.1, step: 0.05, min: 0.01, max: 0.99 }],
  seq_missing: [
    { name: 'p', default: 0.1, step: 0.05, min: 0.01, max: 0.99 },
    { name: 'seq_len', default: 32, step: 1, min: 1 },
  ],
  block_missing: [
    { name: 'factor', default: 0.1, step: 0.05, min: 0.01, max: 0.99 },
    { name: 'block_len', default: 32, step: 1, min: 1 },
    { name: 'block_width', default: 3, step: 1, min: 1 },
  ],
  mar_logistic: [
    { name: 'obs_rate', default: 0.5, step: 0.05, min: 0.01, max: 0.99 },
    { name: 'missing_rate', default: 0.1, step: 0.05, min: 0.01, max: 0.99 },
  ],
  mnar_x: [{ name: 'offset', default: 0.0, step: 0.1 }],
  mnar_t: [
    { name: 'cycle', default: 20, step: 1, min: 1 },
    { name: 'pos', default: 10, step: 1, min: 0 },
    { name: 'scale', default: 3, step: 0.5, min: 0.1 },
  ],
  mnar_nonuniform: [
    { name: 'p', default: 0.1, step: 0.05, min: 0.01, max: 0.99 },
    { name: 'increase_factor', default: 0.5, step: 0.1, min: 0.01 },
  ],
};

export const DATASET_PRESETS = [
  { name: 'ETTh1', columns: 'HUFL,HULL,MUFL,MULL,LUFL,LULL,OT', desc: 'Electricity Transformer Hourly 1' },
  { name: 'ETTh2', columns: 'HUFL,HULL,MUFL,MULL,LUFL,LULL,OT', desc: 'Electricity Transformer Hourly 2' },
  { name: 'ETTm1', columns: 'HUFL,HULL,MUFL,MULL,LUFL,LULL,OT', desc: 'Electricity Transformer 15-min 1' },
];

export const CHART_PALETTE = [
  '#1a56c4', // Primary Blue
  '#059669', // Emerald Green
  '#d97706', // Amber
  '#7c3aed', // Purple
  '#0284c7', // Sky
  '#db2777', // Rose
  '#4b5563', // Slate
];
