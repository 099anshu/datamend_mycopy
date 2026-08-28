'use client';

import React from 'react';
import dynamic from 'next/dynamic';
import { Navbar } from '@/components/Navbar';
import { ConfigSidebar } from '@/components/ConfigSidebar';
import { KpiSummaryCards } from '@/components/KpiSummaryCards';
import { AnomaliesTable } from '@/components/AnomaliesTable';
import { ErrorBoundary } from '@/components/common/ErrorBoundary';
import { useDashboardState } from '@/hooks/useDashboardState';
import { AlertCircle, Radio } from 'lucide-react';

// Dynamic lazy loading for heavy SVG charting modules with fallback skeletons
const TimeSeriesMultiChart = dynamic(
  () =>
    import('@/components/TimeSeriesMultiChart').then((mod) => mod.TimeSeriesMultiChart),
  {
    ssr: false,
    loading: () => (
      <div className="panel" style={{ height: 360, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <span style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>Loading Time-Series Visualization...</span>
      </div>
    ),
  }
);

const AnomalyScoreChart = dynamic(
  () =>
    import('@/components/AnomalyScoreChart').then((mod) => mod.AnomalyScoreChart),
  { ssr: false }
);

const DifferenceBaselineChart = dynamic(
  () =>
    import('@/components/DifferenceBaselineChart').then((mod) => mod.DifferenceBaselineChart),
  { ssr: false }
);

const FeatureHeatmapChart = dynamic(
  () =>
    import('@/components/FeatureHeatmapChart').then((mod) => mod.FeatureHeatmapChart),
  { ssr: false }
);

const SeverityDistributionChart = dynamic(
  () =>
    import('@/components/SeverityDistributionChart').then((mod) => mod.SeverityDistributionChart),
  { ssr: false }
);

export default function DashboardPage() {
  const {
    status,
    statusMessage,
    errorMessage,
    setErrorMessage,
    scoresData,
    anomalies,
    activeColumns,
    currentThreshold,
    rollingWindow,
    setRollingWindow,
    showRolling,
    setShowRolling,
    showAnomaliesOnly,
    setShowAnomaliesOnly,
    chartData,
    isBusy,
    handleFetchScores,
    handleRunAnalyze,
  } = useDashboardState();

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', backgroundColor: 'var(--bg-page)' }}>
      <Navbar status={status} statusMessage={statusMessage} />

      <main role="main" style={{ flex: 1, padding: '16px 20px', maxWidth: 1680, margin: '0 auto', width: '100%' }}>
        {/* Error Alert Box */}
        {errorMessage && (
          <div
            role="alert"
            style={{
              padding: '10px 14px',
              marginBottom: 14,
              backgroundColor: 'var(--status-critical-bg)',
              border: '1px solid #fecaca',
              borderRadius: 4,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: 10,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#991b1b' }}>
              <AlertCircle size={15} />
              <span style={{ fontSize: '0.8125rem', fontWeight: 600 }}>{errorMessage}</span>
            </div>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setErrorMessage(null)}
              style={{ padding: '2px 8px', fontSize: '0.6875rem' }}
              aria-label="Dismiss error"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Live SSE Status Box */}
        {status === 'analyzing' && (
          <div
            role="status"
            aria-live="polite"
            style={{
              padding: '10px 14px',
              marginBottom: 14,
              backgroundColor: 'var(--status-info-bg)',
              border: '1px solid #bfdbfe',
              borderRadius: 4,
              display: 'flex',
              alignItems: 'center',
              gap: 10,
            }}
          >
            <Radio size={15} color="var(--status-info)" className="animate-spin" />
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: '0.8125rem', fontWeight: 700, color: '#1e40af' }}>
                Real-Time Analysis in Progress
              </div>
              <div style={{ fontSize: '0.75rem', color: '#2563eb' }}>
                {statusMessage}
              </div>
            </div>
          </div>
        )}

        {/* Main 2-Column Layout */}
        <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr', gap: 16, alignItems: 'start' }}>
          {/* Left Column: Pipeline Configuration */}
          <ConfigSidebar
            onFetchScores={handleFetchScores}
            onRunAnalyze={handleRunAnalyze}
            isBusy={isBusy}
            activeStatus={status}
          />

          {/* Right Column: Visual Dashboard */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {/* KPI Cards */}
            <ErrorBoundary fallbackTitle="KPI Summary Metrics Error">
              <KpiSummaryCards
                scores={scoresData?.scores || []}
                anomalies={anomalies}
                missingRate={scoresData?.missingRate}
                missingValueHandling={scoresData?.missingValueHandling}
                status={status}
              />
            </ErrorBoundary>

            {/* Primary Time Series Visualization */}
            <ErrorBoundary fallbackTitle="Multi-Series Chart Error">
              <TimeSeriesMultiChart
                data={chartData}
                columns={activeColumns}
                rollingWindow={rollingWindow}
                onRollingWindowChange={setRollingWindow}
                showRolling={showRolling}
                onToggleRolling={() => setShowRolling((v) => !v)}
                showAnomaliesOnly={showAnomaliesOnly}
                onToggleAnomaliesOnly={() => setShowAnomaliesOnly((v) => !v)}
              />
            </ErrorBoundary>

            {/* TimeRCD Anomaly Score Curve & Cutoff Boundary */}
            <ErrorBoundary fallbackTitle="Score Boundary Chart Error">
              <AnomalyScoreChart data={chartData} threshold={currentThreshold} />
            </ErrorBoundary>

            {/* Baseline Deviation / Actual vs Perceived Difference (Observable Insight) */}
            <ErrorBoundary fallbackTitle="Baseline Deviation Chart Error">
              <DifferenceBaselineChart
                data={chartData}
                columns={activeColumns}
                rollingWindow={rollingWindow}
              />
            </ErrorBoundary>

            {/* Feature × Time Anomaly Matrix Heatmap */}
            <ErrorBoundary fallbackTitle="Feature Heatmap Error">
              <FeatureHeatmapChart data={chartData} columns={activeColumns} />
            </ErrorBoundary>

            {/* Severity and Column Breakdown Charts */}
            <ErrorBoundary fallbackTitle="Severity Distribution Error">
              <SeverityDistributionChart anomalies={anomalies} columns={activeColumns} />
            </ErrorBoundary>

            {/* Detailed Anomalies Table */}
            <ErrorBoundary fallbackTitle="Anomalies Table Error">
              <AnomaliesTable anomalies={anomalies} />
            </ErrorBoundary>
          </div>
        </div>
      </main>
    </div>
  );
}
