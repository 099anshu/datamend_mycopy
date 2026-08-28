'use client';

import React from 'react';
import {
  Sliders,
  Play,
  RotateCcw,
  Zap,
  BarChart3,
} from 'lucide-react';
import {
  AnalysisRequestPayload,
  CorruptionMethod,
  MissingValueStrategy,
} from '@/types/api';
import { CORRUPTION_PARAM_CONFIGS, DATASET_PRESETS } from '@/lib/config';
import { usePipelineConfig } from '@/hooks/usePipelineConfig';

interface ConfigSidebarProps {
  onFetchScores: (payload: AnalysisRequestPayload) => void;
  onRunAnalyze: (payload: AnalysisRequestPayload) => void;
  isBusy: boolean;
  activeStatus: string;
}

export const ConfigSidebar: React.FC<ConfigSidebarProps> = ({
  onFetchScores,
  onRunAnalyze,
  isBusy,
}) => {
  const {
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
    corruptionParams,
    mvhStrategy,
    setMvhStrategy,
    handleMethodChange,
    handleParamChange,
    handleApplyPreset,
    buildPayload,
    handleReset,
  } = usePipelineConfig();

  return (
    <aside
      className="panel"
      role="region"
      aria-label="Pipeline Configuration"
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: 'fit-content',
        position: 'sticky',
        top: 68,
      }}
    >
      <div className="panel-header">
        <div className="panel-header-title">
          <Sliders size={15} />
          <span>Parameters</span>
        </div>

      </div>

      <div className="panel-body" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        {/* Dataset Selection */}
        <div className="form-group">
          <label className="form-label" htmlFor="dataset-input">
            Time-Series Dataset (TSDB)
          </label>
          <input
            id="dataset-input"
            type="text"
            className="form-input"
            value={datasetName}
            onChange={(e) => setDatasetName(e.target.value)}
            placeholder="e.g. ETTh1, ETTm1, electricity"
            aria-label="Dataset Name"
          />
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 4 }}>
            {DATASET_PRESETS.map((p) => {
              const isSelected = datasetName === p.name;
              return (
                <button
                  key={p.name}
                  type="button"
                  onClick={() => handleApplyPreset(p)}
                  aria-label={`Apply ${p.name} preset`}
                  style={{
                    backgroundColor: isSelected ? '#1c4b5a' : '#ffffff',
                    border: `1px solid ${isSelected ? '#1c4b5a' : 'var(--border)'}`,
                    color: isSelected ? '#ffffff' : 'var(--text-secondary)',
                    borderRadius: 3,
                    padding: '2px 6px',
                    fontSize: '0.6875rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  {p.name}
                </button>
              );
            })}
          </div>
        </div>

        {/* Features / Columns */}
        <div className="form-group">
          <label className="form-label" htmlFor="columns-input">
            Signal Columns
          </label>
          <textarea
            id="columns-input"
            className="form-input"
            rows={2}
            value={columnsInput}
            onChange={(e) => setColumnsInput(e.target.value)}
            style={{ resize: 'vertical', fontSize: '0.8125rem' }}
            aria-label="Sensor Signals"
          />
        </div>

        {/* Model & Threshold */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label" htmlFor="detector-select">Detector</label>
            <select
              id="detector-select"
              className="form-select"
              value={detector}
              onChange={(e) => setDetector(e.target.value)}
              aria-label="Anomaly Detector Model"
            >
              <option value="timercd">TimeRCD</option>
            </select>
          </div>

          <div className="form-group" style={{ marginBottom: 0 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <label className="form-label" htmlFor="threshold-range">Threshold</label>
              <span className="tabular-nums" style={{ fontSize: '0.75rem', color: 'var(--accent)', fontWeight: 700 }}>
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
              style={{ width: '100%', accentColor: 'var(--panel-header)', marginTop: 6 }}
              aria-label="Anomaly Score Threshold"
            />
          </div>
        </div>

        <hr style={{ borderColor: 'var(--border)', borderStyle: 'solid', borderWidth: '1px 0 0 0' }} />

        {/* PyGrinder Corruption */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer', fontSize: '0.8125rem', fontWeight: 600, color: 'var(--text-primary)' }}>
              <input
                type="checkbox"
                checked={corruptionEnabled}
                onChange={(e) => {
                  setCorruptionEnabled(e.target.checked);
                  if (e.target.checked && mvhStrategy === 'reject') {
                    setMvhStrategy('ffill');
                  }
                }}
                style={{ accentColor: 'var(--accent)', width: 14, height: 14 }}
              />
              PyGrinder Corruption
            </label>
            {corruptionEnabled && (
              <span className="chip chip-warning" style={{ fontSize: '0.625rem' }}>
                ON
              </span>
            )}
          </div>

          {corruptionEnabled && (
            <div
              style={{
                backgroundColor: '#f8f9fa',
                padding: '10px',
                borderRadius: '4px',
                border: '1px solid var(--border)',
                display: 'flex',
                flexDirection: 'column',
                gap: 8,
              }}
            >
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label className="form-label" htmlFor="corruption-method-select">Mechanism</label>
                <select
                  id="corruption-method-select"
                  className="form-select"
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

              {/* Dynamic Param Inputs */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(80px, 1fr))', gap: 6 }}>
                {CORRUPTION_PARAM_CONFIGS[corruptionMethod]?.map((param) => (
                  <div key={param.name}>
                    <label className="form-label" htmlFor={`param-${param.name}`} style={{ fontSize: '0.625rem' }}>
                      {param.name}
                    </label>
                    <input
                      id={`param-${param.name}`}
                      type="number"
                      step={param.step}
                      min={param.min}
                      max={param.max}
                      className="form-input tabular-nums"
                      value={corruptionParams[param.name] ?? param.default}
                      onChange={(e) => handleParamChange(param.name, parseFloat(e.target.value))}
                      style={{ padding: '3px 6px', fontSize: '0.75rem' }}
                    />
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Missing Value Handling Strategy */}
        <div className="form-group">
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

        {/* Action Triggers */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 4 }}>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => onFetchScores(buildPayload())}
            disabled={isBusy}
            style={{ width: '100%' }}
          >
            1. Load Series &amp; Scores
          </button>

          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => onRunAnalyze(buildPayload())}
            disabled={isBusy}
            style={{ width: '100%' }}
          >
            2. Run Anomaly Detection (Async)
          </button>
        </div>
      </div>
    </aside>
  );
};
