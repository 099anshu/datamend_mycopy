import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import {
  AnalysisRequestPayload,
  CorruptionMethod,
  MissingValueStrategy,
  ScoresResponse,
  AnomalyItem,
} from '../services/schemas';

interface ConfigSlice {
  datasetName: string;
  columnsInput: string;
  detector: string;
  threshold: number;
  corruptionEnabled: boolean;
  corruptionMethod: CorruptionMethod;
  corruptionParams: Record<string, number>;
  mvhStrategy: MissingValueStrategy;
  rollingWindow: number;
  showRolling: boolean;
  showAnomaliesOnly: boolean;

  setDatasetName: (name: string) => void;
  setColumnsInput: (cols: string) => void;
  setDetector: (det: string) => void;
  setThreshold: (thresh: number) => void;
  setCorruptionEnabled: (enabled: boolean) => void;
  setCorruptionMethod: (method: CorruptionMethod) => void;
  setCorruptionParams: (params: Record<string, number>) => void;
  setMvhStrategy: (strategy: MissingValueStrategy) => void;
  setRollingWindow: (window: number) => void;
  setShowRolling: (show: boolean) => void;
  setShowAnomaliesOnly: (show: boolean) => void;
  resetConfig: () => void;
}

interface AnalysisSlice {
  activeAnalysisId: string | null;
  status: 'idle' | 'loading_scores' | 'scores_ready' | 'analyzing' | 'completed' | 'error';
  statusMessage: string;
  errorMessage: string | null;
  scoresData: ScoresResponse | null;
  anomalies: AnomalyItem[];
  activeColumns: string[];

  setActiveAnalysisId: (id: string | null) => void;
  setStatus: (status: AnalysisSlice['status']) => void;
  setStatusMessage: (msg: string) => void;
  setErrorMessage: (err: string | null) => void;
  setScoresData: (data: ScoresResponse | null) => void;
  setAnomalies: (anomalies: AnomalyItem[]) => void;
  setActiveColumns: (cols: string[]) => void;
  clearError: () => void;
}

export type AnalysisStore = ConfigSlice & AnalysisSlice;

const initialConfig = {
  datasetName: 'ETTh1',
  columnsInput: 'HUFL,HULL,MUFL,MULL,LUFL,LULL,OT',
  detector: 'timercd',
  threshold: 0.8,
  corruptionEnabled: false,
  corruptionMethod: 'mcar' as CorruptionMethod,
  corruptionParams: { p: 0.1 },
  mvhStrategy: 'reject' as MissingValueStrategy,
  rollingWindow: 24,
  showRolling: true,
  showAnomaliesOnly: false,
};

export const useAnalysisStore = create<AnalysisStore>()(
  persist(
    (set) => ({
      ...initialConfig,

      setDatasetName: (datasetName) => set({ datasetName }),
      setColumnsInput: (columnsInput) => set({ columnsInput }),
      setDetector: (detector) => set({ detector }),
      setThreshold: (threshold) => set({ threshold }),
      setCorruptionEnabled: (corruptionEnabled) => set({ corruptionEnabled }),
      setCorruptionMethod: (corruptionMethod) => set({ corruptionMethod }),
      setCorruptionParams: (corruptionParams) => set({ corruptionParams }),
      setMvhStrategy: (mvhStrategy) => set({ mvhStrategy }),
      setRollingWindow: (rollingWindow) => set({ rollingWindow }),
      setShowRolling: (showRolling) => set({ showRolling }),
      setShowAnomaliesOnly: (showAnomaliesOnly) => set({ showAnomaliesOnly }),
      resetConfig: () => set({ ...initialConfig }),

      // Analysis State
      activeAnalysisId: null,
      status: 'idle',
      statusMessage: 'System ready',
      errorMessage: null,
      scoresData: null,
      anomalies: [],
      activeColumns: ['HUFL', 'HULL', 'MUFL', 'MULL', 'LUFL', 'LULL', 'OT'],

      setActiveAnalysisId: (activeAnalysisId) => set({ activeAnalysisId }),
      setStatus: (status) => set({ status }),
      setStatusMessage: (statusMessage) => set({ statusMessage }),
      setErrorMessage: (errorMessage) => set({ errorMessage }),
      setScoresData: (scoresData) => set({ scoresData }),
      setAnomalies: (anomalies) => set({ anomalies }),
      setActiveColumns: (activeColumns) => set({ activeColumns }),
      clearError: () => set({ errorMessage: null }),
    }),
    {
      name: 'datamend-config-v1',
      partialize: (state) => ({
        datasetName: state.datasetName,
        columnsInput: state.columnsInput,
        detector: state.detector,
        threshold: state.threshold,
        rollingWindow: state.rollingWindow,
      }),
    }
  )
);
