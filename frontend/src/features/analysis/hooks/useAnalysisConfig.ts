import { useCallback } from 'react';
import { useAnalysisStore } from './useAnalysis';
import { AnalysisRequestPayload, CorruptionMethod, MissingValueStrategy } from '../services/schemas';
import { CORRUPTION_PARAM_CONFIGS, DATASET_PRESETS } from '@/lib/config';

export function useAnalysisConfig() {
  const store = useAnalysisStore();

  const handleMethodChange = useCallback(
    (method: CorruptionMethod) => {
      store.setCorruptionMethod(method);
      const defaults: Record<string, number> = {};
      CORRUPTION_PARAM_CONFIGS[method]?.forEach((p) => {
        defaults[p.name] = p.default;
      });
      store.setCorruptionParams(defaults);
    },
    [store]
  );

  const handleParamChange = useCallback(
    (name: string, val: number) => {
      store.setCorruptionParams({ ...store.corruptionParams, [name]: val });
    },
    [store]
  );

  const handleApplyPreset = useCallback(
    (preset: (typeof DATASET_PRESETS)[0]) => {
      store.setDatasetName(preset.name);
      store.setColumnsInput(preset.columns);
    },
    [store]
  );

  const buildPayload = useCallback((): AnalysisRequestPayload => {
    const columns = store.columnsInput
      .split(',')
      .map((c) => c.trim())
      .filter(Boolean);

    return {
      analysisId: `ui-${Date.now()}`,
      datasetName: store.datasetName.trim() || 'ETTh1',
      columns: columns.length > 0 ? columns : ['HUFL', 'HULL', 'MUFL', 'MULL', 'LUFL', 'LULL', 'OT'],
      detector: store.detector,
      threshold: store.threshold,
      corruption: store.corruptionEnabled
        ? {
            enabled: true,
            method: store.corruptionMethod,
            params: store.corruptionParams,
          }
        : null,
      missingValueHandling: {
        strategy: store.mvhStrategy,
      },
    };
  }, [store]);

  return {
    ...store,
    handleMethodChange,
    handleParamChange,
    handleApplyPreset,
    buildPayload,
    handleReset: store.resetConfig,
  };
}
