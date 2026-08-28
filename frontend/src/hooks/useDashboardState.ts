import { useState, useMemo, useCallback } from 'react';
import {
  AnalysisDetailResponse,
  AnalysisRequestPayload,
  AnomalyItem,
  DashboardStatus,
  ScoresResponse,
} from '@/types/api';
import { fetchScores, startAnalysis, subscribeToAnalysisEvents } from '@/lib/api';
import { mergeScoresAndAnomalies, downsampleTimeSeries } from '@/lib/transforms';

export function useDashboardState() {
  const [status, setStatus] = useState<DashboardStatus>('idle');
  const [statusMessage, setStatusMessage] = useState('System ready');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const [scoresData, setScoresData] = useState<ScoresResponse | null>(null);
  const [anomalies, setAnomalies] = useState<AnomalyItem[]>([]);
  const [activeColumns, setActiveColumns] = useState<string[]>([
    'HUFL',
    'HULL',
    'MUFL',
    'MULL',
    'LUFL',
    'LULL',
    'OT',
  ]);
  const [currentThreshold, setCurrentThreshold] = useState<number>(0.8);

  // Visualization settings
  const [rollingWindow, setRollingWindow] = useState<number>(24);
  const [showRolling, setShowRolling] = useState<boolean>(true);
  const [showAnomaliesOnly, setShowAnomaliesOnly] = useState<boolean>(false);

  const handleFetchScores = useCallback(async (payload: AnalysisRequestPayload) => {
    setStatus('loading_scores');
    setStatusMessage(`Requesting scores for dataset ${payload.datasetName}...`);
    setErrorMessage(null);
    setActiveColumns(payload.columns);
    setCurrentThreshold(payload.threshold);

    try {
      const res = await fetchScores(payload);
      setScoresData(res);
      setStatus('scores_ready');
      setStatusMessage(`Loaded ${res.scores.length} timestamps from ${payload.datasetName}`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to fetch scores';
      setStatus('error');
      setErrorMessage(msg);
      setStatusMessage('Error loading scores');
    }
  }, []);

  const handleRunAnalyze = useCallback(
    async (payload: AnalysisRequestPayload) => {
      setStatus('analyzing');
      setStatusMessage('Initiating asynchronous analysis & SSE connection...');
      setErrorMessage(null);
      setActiveColumns(payload.columns);
      setCurrentThreshold(payload.threshold);

      try {
        // Pre-fetch scores in parallel if not present
        if (!scoresData || scoresData.scores.length === 0) {
          fetchScores(payload)
            .then((res) => setScoresData(res))
            .catch((e: unknown) => {
              const warnMsg = e instanceof Error ? e.message : String(e);
              console.warn('Background score pre-fetch error:', warnMsg);
            });
        }

        const job = await startAnalysis(payload);
        setStatusMessage(`Job running. Streaming real-time updates...`);

        const unsubscribe = subscribeToAnalysisEvents(job.analysisId, {
          onStatus: (st) => {
            setStatusMessage(`Analysis status: ${st}...`);
          },
          onCompleted: (res: AnalysisDetailResponse) => {
            setAnomalies(res.anomalies || []);
            setStatus('completed');
            setStatusMessage(`Analysis completed! Found ${(res.anomalies || []).length} anomalies.`);
          },
          onError: (err: string) => {
            setStatus('error');
            setErrorMessage(err);
            setStatusMessage('Analysis execution error');
          },
        });

        return unsubscribe;
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Failed to start analysis';
        setStatus('error');
        setErrorMessage(msg);
        setStatusMessage('Error initiating analysis');
        return () => {};
      }
    },
    [scoresData]
  );

  // Full merged dataset with linear O(N) rolling window calculation
  const processedData = useMemo(() => {
    if (!scoresData || !scoresData.scores) return [];
    return mergeScoresAndAnomalies(
      scoresData.scores,
      anomalies,
      activeColumns,
      showRolling ? rollingWindow : 0
    );
  }, [scoresData, anomalies, activeColumns, showRolling, rollingWindow]);

  // Downsampled view for dense chart rendering
  const chartData = useMemo(() => {
    return downsampleTimeSeries(processedData, 1200);
  }, [processedData]);

  const isBusy = status === 'loading_scores' || status === 'analyzing';

  return {
    status,
    statusMessage,
    errorMessage,
    setErrorMessage,
    scoresData,
    anomalies,
    activeColumns,
    setActiveColumns,
    currentThreshold,
    rollingWindow,
    setRollingWindow,
    showRolling,
    setShowRolling,
    showAnomaliesOnly,
    setShowAnomaliesOnly,
    processedData,
    chartData,
    isBusy,
    handleFetchScores,
    handleRunAnalyze,
  };
}
