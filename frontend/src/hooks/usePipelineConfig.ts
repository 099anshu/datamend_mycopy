import { useState, useCallback } from 'react';
import {
  AnalysisRequestPayload,
  CorruptionMethod,
  MissingValueStrategy,
} from '@/types/api';
import { CORRUPTION_PARAM_CONFIGS, DATASET_PRESETS } from '@/lib/config';

export function usePipelineConfig() {
  const [datasetName, setDatasetName] = useState('ETTh1');
  const [columnsInput, setColumnsInput] = useState('HUFL,HULL,MUFL,MULL,LUFL,LULL,OT');
  const [detector, setDetector] = useState('timercd');
  const [threshold, setThreshold] = useState(0.8);

  // Corruption
  const [corruptionEnabled, setCorruptionEnabled] = useState(false);
  const [corruptionMethod, setCorruptionMethod] = useState<CorruptionMethod>('mcar');
  const [corruptionParams, setCorruptionParams] = useState<Record<string, number>>({ p: 0.1 });

  // Missing Value Handling
  const [mvhStrategy, setMvhStrategy] = useState<MissingValueStrategy>('reject');

  const handleMethodChange = useCallback((method: CorruptionMethod) => {
    setCorruptionMethod(method);
    const defaults: Record<string, number> = {};
    CORRUPTION_PARAM_CONFIGS[method]?.forEach((p) => {
      defaults[p.name] = p.default;
    });
    setCorruptionParams(defaults);
  }, []);

  const handleParamChange = useCallback((name: string, val: number) => {
    setCorruptionParams((prev) => ({ ...prev, [name]: val }));
  }, []);

  const handleApplyPreset = useCallback((preset: (typeof DATASET_PRESETS)[0]) => {
    setDatasetName(preset.name);
    setColumnsInput(preset.columns);
  }, []);

  const buildPayload = useCallback((): AnalysisRequestPayload => {
    const columns = columnsInput
      .split(',')
      .map((c) => c.trim())
      .filter(Boolean);

    return {
      analysisId: `ui-${Date.now()}`,
      datasetName: datasetName.trim() || 'ETTh1',
      columns: columns.length > 0 ? columns : ['HUFL', 'HULL', 'MUFL', 'MULL', 'LUFL', 'LULL', 'OT'],
      detector,
      threshold,
      corruption: corruptionEnabled
        ? {
            enabled: true,
            method: corruptionMethod,
            params: corruptionParams,
          }
        : null,
      missingValueHandling: {
        strategy: mvhStrategy,
      },
    };
  }, [
    datasetName,
    columnsInput,
    detector,
    threshold,
    corruptionEnabled,
    corruptionMethod,
    corruptionParams,
    mvhStrategy,
  ]);

  const handleReset = useCallback(() => {
    setDatasetName('ETTh1');
    setColumnsInput('HUFL,HULL,MUFL,MULL,LUFL,LULL,OT');
    setDetector('timercd');
    setThreshold(0.8);
    setCorruptionEnabled(false);
    setCorruptionMethod('mcar');
    setCorruptionParams({ p: 0.1 });
    setMvhStrategy('reject');
  }, []);

  return {
    datasetName,
    setDatasetName,
    columnsInput,
    setColumnsInput,
    detector,
    setDetector,
    threshold,
    setThreshold,
    corruptionEnabled,
    setCorruptionEnabled,
    corruptionMethod,
    setCorruptionMethod,
    corruptionParams,
    mvhStrategy,
    setMvhStrategy,
    handleMethodChange,
    handleParamChange,
    handleApplyPreset,
    buildPayload,
    handleReset,
  };
}
