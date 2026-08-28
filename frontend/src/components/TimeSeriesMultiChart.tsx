'use client';

import React, { useState, useMemo } from 'react';
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Brush,
  CartesianGrid,
} from 'recharts';
import { Layers, Eye, SlidersHorizontal } from 'lucide-react';
import { ProcessedTimeSeriesPoint } from '@/lib/transforms';

const PALETTE = [
  '#1a56c4', // Blue
  '#059669', // Emerald
  '#d97706', // Amber
  '#7c3aed', // Purple
  '#0284c7', // Sky
  '#db2777', // Rose
  '#4b5563', // Slate
];

interface TimeSeriesMultiChartProps {
  data: ProcessedTimeSeriesPoint[];
  columns: string[];
  rollingWindow: number;
  onRollingWindowChange: (w: number) => void;
  showRolling: boolean;
  onToggleRolling: () => void;
  showAnomaliesOnly: boolean;
  onToggleAnomaliesOnly: () => void;
}

export const TimeSeriesMultiChart: React.FC<TimeSeriesMultiChartProps> = ({
  data,
  columns,
  rollingWindow,
  onRollingWindowChange,
  showRolling,
  onToggleRolling,
  showAnomaliesOnly,
  onToggleAnomaliesOnly,
}) => {
  const [activeColumns, setActiveColumns] = useState<string[]>(columns);

  // Sync active columns if columns change
  React.useEffect(() => {
    setActiveColumns(columns);
  }, [columns]);

  const toggleColumn = (col: string) => {
    setActiveColumns((prev) =>
      prev.includes(col) ? prev.filter((c) => c !== col) : [...prev, col]
    );
  };

  const chartData = useMemo(() => {
    if (!showAnomaliesOnly) return data;
    return data.filter((d) => d.isAnomaly);
  }, [data, showAnomaliesOnly]);

  if (data.length === 0) {
    return (
      <div
        className="panel"
        style={{
          height: 360,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 8,
          color: 'var(--text-muted)',
        }}
      >
        <Layers size={32} color="#cbd5e1" />
        <p style={{ fontSize: '0.8125rem' }}>
          No time-series data loaded. Click &quot;1. Load Series &amp; Scores&quot; to fetch signals.
        </p>
      </div>
    );
  }

  return (
    <div className="panel">
      {/* Edge-to-edge Section Header Bar */}
      <div className="panel-header">
        <div className="panel-header-title">
          <span>Multivariate Time-Series &amp; Anomaly Overlay</span>
        </div>

        {/* Action Toggles */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={onToggleRolling}
            style={{
              padding: '3px 8px',
              fontSize: '0.6875rem',
              backgroundColor: showRolling ? '#f1f5f9' : '#ffffff',
              borderColor: showRolling ? '#94a3b8' : 'var(--border)',
            }}
          >
            <SlidersHorizontal size={12} />
            SMA ({rollingWindow})
          </button>

          {showRolling && (
            <select
              className="form-select tabular-nums"
              value={rollingWindow}
              onChange={(e) => onRollingWindowChange(parseInt(e.target.value, 10))}
              style={{ width: 'auto', padding: '2px 6px', fontSize: '0.6875rem' }}
            >
              <option value="6">6 steps</option>
              <option value="12">12 steps</option>
              <option value="24">24 steps (1d)</option>
              <option value="48">48 steps (2d)</option>
              <option value="168">168 steps (7d)</option>
            </select>
          )}

          <button
            type="button"
            className="btn btn-secondary"
            onClick={onToggleAnomaliesOnly}
            style={{
              padding: '3px 8px',
              fontSize: '0.6875rem',
              backgroundColor: showAnomaliesOnly ? '#fee2e2' : '#ffffff',
              color: showAnomaliesOnly ? '#991b1b' : 'var(--text-primary)',
              borderColor: showAnomaliesOnly ? '#fca5a5' : 'var(--border)',
            }}
          >
            <Eye size={12} />
            {showAnomaliesOnly ? 'Anomalies Only' : 'All Data'}
          </button>
        </div>
      </div>

      <div className="panel-body" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {/* Signal Channel Toggles */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, alignItems: 'center' }}>
          <span style={{ fontSize: '0.6875rem', color: 'var(--text-secondary)', textTransform: 'uppercase', fontWeight: 600, marginRight: 4 }}>
            Channels:
          </span>
          {columns.map((col, idx) => {
            const color = PALETTE[idx % PALETTE.length];
            const isVisible = activeColumns.includes(col);
            return (
              <button
                key={col}
                type="button"
                onClick={() => toggleColumn(col)}
                style={{
                  backgroundColor: isVisible ? '#ffffff' : '#f8f9fa',
                  border: `1px solid ${isVisible ? color : 'var(--border)'}`,
                  color: isVisible ? color : 'var(--text-muted)',
                  padding: '2px 7px',
                  borderRadius: 3,
                  fontSize: '0.6875rem',
                  fontWeight: 700,
                  cursor: 'pointer',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 4,
                }}
              >
                <span style={{ width: 6, height: 6, borderRadius: '50%', backgroundColor: isVisible ? color : '#cbd5e1' }} />
                {col}
              </button>
            );
          })}
        </div>

        {/* Chart */}
        <div style={{ width: '100%', height: 360 }}>
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={chartData} margin={{ top: 8, right: 16, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis
                dataKey="formattedTime"
                stroke="#64748b"
                fontSize={11}
                tickLine={false}
                interval="preserveStartEnd"
                minTickGap={40}
              />
              <YAxis stroke="#64748b" fontSize={11} tickLine={false} domain={['auto', 'auto']} />
              <Tooltip
                content={({ active, payload }) => {
                  if (!active || !payload || !payload.length) return null;
                  const point = payload[0].payload as ProcessedTimeSeriesPoint;
                  return (
                    <div
                      style={{
                        backgroundColor: '#ffffff',
                        border: '1px solid var(--border)',
                        padding: '10px 12px',
                        borderRadius: 4,
                        boxShadow: '0 2px 8px rgba(0, 0, 0, 0.08)',
                        fontSize: '0.75rem',
                        minWidth: 180,
                      }}
                    >
                      <div style={{ fontWeight: 700, color: 'var(--text-primary)', marginBottom: 4, borderBottom: '1px solid var(--border)', paddingBottom: 2 }}>
                        {point.timestamp}
                      </div>

                      {point.isAnomaly && (
                        <div style={{ marginBottom: 6 }}>
                          <span
                            className={`chip ${
                              point.anomalySeverity === 'HIGH'
                                ? 'chip-critical'
                                : point.anomalySeverity === 'MEDIUM'
                                ? 'chip-warning'
                                : 'chip-info'
                            }`}
                          >
                            ANOMALY ({point.anomalySeverity}) · Score: {point.score}
                          </span>
                        </div>
                      )}

                      <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                        {activeColumns.map((col, i) => (
                          <div key={col} style={{ display: 'flex', justifyContent: 'space-between', gap: 10 }}>
                            <span style={{ color: PALETTE[i % PALETTE.length], fontWeight: 600 }}>{col}:</span>
                            <span className="tabular-nums" style={{ color: 'var(--text-primary)', fontWeight: 700 }}>
                              {point[col] !== undefined ? String(point[col]) : '—'}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                }}
              />

              {/* Signal Lines */}
              {activeColumns.map((col, idx) => {
                const color = PALETTE[idx % PALETTE.length];
                return (
                  <Line
                    key={col}
                    type="monotone"
                    dataKey={col}
                    name={col}
                    stroke={color}
                    strokeWidth={1.5}
                    dot={false}
                    activeDot={{ r: 4, fill: color, stroke: '#ffffff', strokeWidth: 1.5 }}
                  />
                );
              })}

              {/* Rolling Average Lines */}
              {showRolling &&
                activeColumns.map((col, idx) => {
                  const color = PALETTE[idx % PALETTE.length];
                  return (
                    <Line
                      key={`${col}_rolling`}
                      type="monotone"
                      dataKey={`${col}_rolling`}
                      name={`${col} (SMA ${rollingWindow})`}
                      stroke={color}
                      strokeWidth={1.5}
                      strokeDasharray="4 4"
                      dot={false}
                      opacity={0.7}
                    />
                  );
                })}

              {/* Brush */}
              <Brush
                dataKey="formattedTime"
                height={26}
                stroke="#1c4b5a"
                fill="#f1f3f5"
                travellerWidth={8}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};
