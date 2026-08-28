'use client';

import React, { useCallback } from 'react';
import { Navbar } from '@/components/Navbar';
import {
  AnalysisConfig,
  useAnalysisStore,
  useAnalysisSSE,
  fetchScoresApi,
  startAnalysisApi,
  AnalysisRequestPayload,
} from '@/features/analysis';
import {
  TimeSeriesChart,
  ScoreCurveChart,
  BaselineDeviationChart,
  HeatmapChart,
  SeverityCharts,
  KpiCards,
  AnomaliesTable,
  useChartData,
  useChartSync,
} from '@/features/visualization';
import { AlertCircle, Radio } from 'lucide-react';

export default function DashboardPage() {
  const store = useAnalysisStore();
  const chartData = useChartData();
  const syncGroupId = useChartSync(true);

  useAnalysisSSE({
    analysisId: store.activeAnalysisId,
    onStatus: (st) => store.setStatusMessage(`Analysis status: ${st}...`),
    onCompleted: (res) => {
      store.setAnomalies(res.anomalies || []);
      store.setStatus('completed');
      store.setStatusMessage(`Analysis completed! Found ${(res.anomalies || []).length} anomalies.`);
    },
    onError: (err) => {
      store.setStatus('error');
      store.setErrorMessage(err);
      store.setStatusMessage('Analysis execution error');
    },
  });

  const handleFetchScores = useCallback(
    async (payload: AnalysisRequestPayload) => {
      store.setStatus('loading_scores');
      store.setStatusMessage(`Requesting scores for ${payload.datasetName}...`);
      store.clearError();
      store.setActiveColumns(payload.columns);
      store.setThreshold(payload.threshold);
      try {
        const res = await fetchScoresApi(payload);
        store.setScoresData(res);
        store.setStatus('scores_ready');
        store.setStatusMessage(`Loaded ${res.scores.length} timestamps from ${payload.datasetName}`);
      } catch (err: unknown) {
        store.setStatus('error');
        store.setErrorMessage(err instanceof Error ? err.message : 'Failed to fetch scores');
      }
    },
    [store]
  );

  const handleRunAnalyze = useCallback(
    async (payload: AnalysisRequestPayload) => {
      store.setStatus('analyzing');
      store.setStatusMessage('Starting asynchronous analysis & SSE stream...');
      store.clearError();
      store.setActiveColumns(payload.columns);
      store.setThreshold(payload.threshold);
      try {
        if (!store.scoresData || store.scoresData.scores.length === 0) {
          fetchScoresApi(payload)
            .then((res) => store.setScoresData(res))
            .catch(() => {});
        }
        const job = await startAnalysisApi(payload);
        store.setActiveAnalysisId(job.analysisId);
        store.setStatusMessage('Streaming real-time analysis events...');
      } catch (err: unknown) {
        store.setStatus('error');
        store.setErrorMessage(err instanceof Error ? err.message : 'Failed to start analysis');
      }
    },
    [store]
  );

  const isBusy = store.status === 'loading_scores' || store.status === 'analyzing';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', backgroundColor: '#eef0f3' }}>
      <Navbar status={store.status} statusMessage={store.statusMessage} />

      <main style={{ flex: 1, padding: 16, maxWidth: 1680, width: '100%', margin: '0 auto', boxSizing: 'border-box' }}>

        {/* Error alert */}
        {store.errorMessage && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: 12,
              padding: '10px 14px',
              marginBottom: 12,
              backgroundColor: '#fef2f2',
              border: '1px solid #fecaca',
              borderRadius: 6,
              color: '#991b1b',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <AlertCircle size={15} color="#ef4444" style={{ flexShrink: 0 }} />
              <span style={{ fontSize: '0.75rem', fontWeight: 600 }}>{store.errorMessage}</span>
            </div>
            <button className="btn btn-secondary" onClick={store.clearError} style={{ padding: '3px 10px' }}>
              Dismiss
            </button>
          </div>
        )}

        {/* SSE status banner */}
        {store.status === 'analyzing' && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              padding: '10px 14px',
              marginBottom: 12,
              backgroundColor: '#eff6ff',
              border: '1px solid #bfdbfe',
              borderRadius: 6,
              color: '#1e3a8a',
            }}
          >
            <Radio size={15} color="#1a56c4" style={{ flexShrink: 0 }} />
            <div>
              <div style={{ fontSize: '0.75rem', fontWeight: 700 }}>
                Real-Time Analysis in Progress
              </div>
              <div style={{ fontSize: '0.6875rem', color: '#1a56c4' }}>
                {store.statusMessage}
              </div>
            </div>
          </div>
        )}

        {/* Two-column layout: sidebar + main content */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: '280px 1fr',
            gap: 16,
            alignItems: 'start',
          }}
        >
          {/* Sidebar */}
          <div style={{ position: 'sticky', top: 72 }}>
            <AnalysisConfig
              onFetchScores={handleFetchScores}
              onRunAnalyze={handleRunAnalyze}
              isBusy={isBusy}
            />
          </div>

          {/* Chart content area */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14, minWidth: 0 }}>
            <KpiCards
              scores={store.scoresData?.scores || []}
              anomalies={store.anomalies}
              missingRate={store.scoresData?.missingRate}
              missingValueHandling={store.scoresData?.missingValueHandling}
            />

            <TimeSeriesChart
              data={chartData}
              columns={store.activeColumns}
              rollingWindow={store.rollingWindow}
              onRollingWindowChange={store.setRollingWindow}
              showRolling={store.showRolling}
              onToggleRolling={() => store.setShowRolling(!store.showRolling)}
              showAnomaliesOnly={store.showAnomaliesOnly}
              onToggleAnomaliesOnly={() => store.setShowAnomaliesOnly(!store.showAnomaliesOnly)}
              syncGroupId={syncGroupId}
            />

            <ScoreCurveChart
              data={chartData}
              threshold={store.threshold}
              syncGroupId={syncGroupId}
            />

            <BaselineDeviationChart
              data={chartData}
              columns={store.activeColumns}
              rollingWindow={store.rollingWindow}
              syncGroupId={syncGroupId}
            />

            <HeatmapChart data={chartData} columns={store.activeColumns} />

            <SeverityCharts anomalies={store.anomalies} columns={store.activeColumns} />

            <AnomaliesTable anomalies={store.anomalies} />
          </div>
        </div>
      </main>
    </div>
  );
}
