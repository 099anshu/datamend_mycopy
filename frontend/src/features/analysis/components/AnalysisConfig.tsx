'use client';

import React from 'react';
import { Sliders } from 'lucide-react';
import { AnalysisRequestPayload, CorruptionMethod, MissingValueStrategy } from '../services/schemas';
import { useAnalysisConfig } from '../hooks/useAnalysisConfig';
import { CORRUPTION_PARAM_CONFIGS } from '@/lib/config';
import { Panel } from '@/shared/ui';
import { useDatasetSelection } from '@/features/datasets/hooks/useDatasetSelection';

interface AnalysisConfigProps {
  onFetchScores: (payload: AnalysisRequestPayload) => void;
  onRunAnalyze: (payload: AnalysisRequestPayload) => void;
  isBusy: boolean;
}

export const AnalysisConfig: React.FC<AnalysisConfigProps> = ({
  onFetchScores,
  onRunAnalyze,
  isBusy,
}) => {
  const { isReady, blockingReason } = useDatasetSelection();
  const {
    detector,
    setDetector,
    threshold,
    setThreshold,
    corruptionEnabled,
    setCorruptionEnabled,
    corruptionMethod,
    corruptionParams,
    mvhStrategy,
    setMvhStrategy,
    handleMethodChange,
    handleParamChange,
    buildPayload,
  } = useAnalysisConfig();

  return (
    <Panel
      title="Parameters"
      icon={<Sliders size={15} />}
      bodyClassName=""
      style={{ overflow: 'visible' }}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        {/* Detector + Threshold */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label" htmlFor="detector-select">
              Detector
            </label>
            <select
              id="detector-select"
              className="form-select"
              value={detector}
              onChange={(e) => setDetector(e.target.value)}
            >
              <option value="timercd">TimeRCD</option>
            </select>
          </div>

          <div className="form-group" style={{ marginBottom: 0 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <label className="form-label" htmlFor="threshold-range">
                Threshold
              </label>
              <span
                className="tabular-nums"
                style={{ fontSize: '0.75rem', fontWeight: 700, color: '#1a56c4' }}
              >
                {threshold.toFixed(2)}
              </span>
            </div>
            <input
              id="threshold-range"
              type="range"
              min="0.1"
              max="0.99"
              step="0.01"
              value={threshold}
              onChange={(e) => setThreshold(parseFloat(e.target.value))}
              style={{ width: '100%', accentColor: '#1c4b5a', marginTop: 6 }}
            />
          </div>
        </div>

        <hr style={{ border: 'none', borderTop: '1px solid #d7dbe0', margin: 0 }} />

        {/* PyGrinder Corruption */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <label
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                cursor: 'pointer',
                fontSize: '0.75rem',
                fontWeight: 600,
                color: '#1e293b',
              }}
            >
              <input
                type="checkbox"
                checked={corruptionEnabled}
                onChange={(e) => {
                  setCorruptionEnabled(e.target.checked);
                  if (e.target.checked && mvhStrategy === 'reject') {
                    setMvhStrategy('ffill');
                  }
                }}
                style={{ accentColor: '#1a56c4', width: 14, height: 14 }}
              />
              PyGrinder Corruption
            </label>
            {corruptionEnabled && (
              <span className="chip chip-warning">ON</span>
            )}
          </div>

          {corruptionEnabled && (
            <div
              style={{
                backgroundColor: '#f8fafc',
                padding: 10,
                borderRadius: 4,
                border: '1px solid #d7dbe0',
                display: 'flex',
                flexDirection: 'column',
                gap: 8,
              }}
            >
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label className="form-label" style={{ fontSize: '0.625rem' }} htmlFor="corruption-method-select">
                  Mechanism
                </label>
                <select
                  id="corruption-method-select"
                  className="form-select"
                  style={{ fontSize: '0.75rem', padding: '4px 8px' }}
                  value={corruptionMethod}
                  onChange={(e) => handleMethodChange(e.target.value as CorruptionMethod)}
                >
                  <option value="mcar">MCAR (Random Missing)</option>
                  <option value="mar_logistic">MAR Logistic</option>
                  <option value="mnar_x">MNAR (Value-based X)</option>
                  <option value="mnar_t">MNAR (Time-based T)</option>
                  <option value="mnar_nonuniform">MNAR Non-Uniform</option>
                  <option value="rdo">RDO (Random Drop Out)</option>
                  <option value="seq_missing">Sequence Missing</option>
                  <option value="block_missing">Block Missing</option>
                </select>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
                {CORRUPTION_PARAM_CONFIGS[corruptionMethod]?.map((param) => (
                  <div key={param.name}>
                    <label
                      className="form-label"
                      style={{ fontSize: '0.625rem' }}
                      htmlFor={`param-${param.name}`}
                    >
                      {param.name}
                    </label>
                    <input
                      id={`param-${param.name}`}
                      type="number"
                      step={param.step}
                      min={param.min}
                      max={param.max}
                      className="form-input tabular-nums"
                      style={{ padding: '4px 8px', fontSize: '0.75rem' }}
                      value={corruptionParams[param.name] ?? param.default}
                      onChange={(e) => handleParamChange(param.name, parseFloat(e.target.value))}
                    />
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Imputation Strategy */}
        <div className="form-group" style={{ marginBottom: 0 }}>
          <label className="form-label" htmlFor="mvh-strategy-select">
            Imputation Strategy
          </label>
          <select
            id="mvh-strategy-select"
            className="form-select"
            value={mvhStrategy}
            onChange={(e) => setMvhStrategy(e.target.value as MissingValueStrategy)}
          >
            <option value="reject">Reject</option>
            <option value="ffill">Forward Fill</option>
            <option value="bfill">Backward Fill</option>
            <option value="mean">Mean</option>
            <option value="interpolate">Linear Interpolation</option>
          </select>
        </div>

        {/* Action Buttons */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => onFetchScores(buildPayload())}
            disabled={isBusy || !isReady}
            title={blockingReason ?? undefined}
            style={{ width: '100%' }}
          >
            1. Load Series &amp; Scores
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => onRunAnalyze(buildPayload())}
            disabled={isBusy || !isReady}
            title={blockingReason ?? undefined}
            style={{ width: '100%' }}
          >
            2. Run Anomaly Detection (Async)
          </button>
        </div>
      </div>
    </Panel>
  );
};
