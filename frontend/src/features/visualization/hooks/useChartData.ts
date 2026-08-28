import { useMemo } from 'react';
import { useAnalysisStore } from '@/features/analysis';
import { useTimeSeriesMerge } from '@/features/data/hooks';

export function useChartData() {
  const scoresData = useAnalysisStore((s) => s.scoresData);
  const anomalies = useAnalysisStore((s) => s.anomalies);
  const activeColumns = useAnalysisStore((s) => s.activeColumns);
  const rollingWindow = useAnalysisStore((s) => s.rollingWindow);
  const showRolling = useAnalysisStore((s) => s.showRolling);

  return useTimeSeriesMerge(
    scoresData?.scores,
    anomalies,
    activeColumns,
    showRolling ? rollingWindow : 0
  );
}
