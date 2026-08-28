'use client';

import React, { useState } from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
  CartesianGrid,
  Cell,
} from 'recharts';
import { Compass } from 'lucide-react';
import { ProcessedTimeSeriesPoint } from '@/lib/transforms';

interface DifferenceBaselineChartProps {
  data: ProcessedTimeSeriesPoint[];
  columns: string[];
  rollingWindow: number;
}

export const DifferenceBaselineChart: React.FC<DifferenceBaselineChartProps> = ({
  data,
  columns,
  rollingWindow,
}) => {
  const [selectedColumn, setSelectedColumn] = useState<string>(columns[0] || 'OT');

  React.useEffect(() => {
    if (columns.length > 0 && !columns.includes(selectedColumn)) {
      setSelectedColumn(columns[0]);
    }
  }, [columns, selectedColumn]);

  if (data.length === 0 || columns.length === 0) return null;

  const diffKey = `${selectedColumn}_diff`;
  const chartData = data.filter((d) => typeof d[diffKey] === 'number');

  if (chartData.length === 0) return null;

  return (
    <div className="panel">
      {/* Edge-to-edge Header Bar */}
      <div className="panel-header">
        <div>
          <div className="panel-header-title">
            <span>Actual vs. Baseline Deviation (Observable)</span>
          </div>
          <div className="panel-header-subtitle">
            True vertical delta against {rollingWindow}-step SMA baseline
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ fontSize: '0.6875rem', color: '#cbd5e1', textTransform: 'uppercase', fontWeight: 600 }}>
            Channel:
          </span>
          <select
            className="form-select"
            value={selectedColumn}
            onChange={(e) => setSelectedColumn(e.target.value)}
            style={{
              width: 'auto',
              padding: '2px 8px',
              fontSize: '0.6875rem',
              backgroundColor: '#ffffff',
              color: 'var(--text-primary)',
            }}
          >
            {columns.map((col) => (
              <option key={col} value={col}>
                {col}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="panel-body">
        <div style={{ width: '100%', height: 200 }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 8, right: 16, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis
                dataKey="formattedTime"
                stroke="#64748b"
                fontSize={10}
                tickLine={false}
                interval="preserveStartEnd"
                minTickGap={40}
              />
              <YAxis stroke="#64748b" fontSize={10} tickLine={false} />
              <Tooltip
                content={({ active, payload }) => {
                  if (!active || !payload || !payload.length) return null;
                  const pt = payload[0].payload as ProcessedTimeSeriesPoint;
                  const diffVal = pt[diffKey] as number;
                  return (
                    <div
                      style={{
                        backgroundColor: '#ffffff',
                        border: '1px solid var(--border)',
                        padding: '8px 10px',
                        borderRadius: 4,
                        boxShadow: '0 2px 8px rgba(0, 0, 0, 0.08)',
                        fontSize: '0.75rem',
                      }}
                    >
                      <div style={{ color: 'var(--text-secondary)', marginBottom: 3 }}>{pt.timestamp}</div>
                      <div>
                        <span>Delta ({selectedColumn}): </span>
                        <strong
                          className="tabular-nums"
                          style={{
                            color: pt.isAnomaly
                              ? 'var(--status-critical)'
                              : diffVal >= 0
                              ? 'var(--accent)'
                              : 'var(--text-secondary)',
                            fontSize: '0.8125rem',
                          }}
                        >
                          {diffVal > 0 ? `+${diffVal.toFixed(3)}` : diffVal.toFixed(3)}
                        </strong>
                      </div>
                    </div>
                  );
                }}
              />
              <ReferenceLine y={0} stroke="#94a3b8" />
              <Bar dataKey={diffKey}>
                {chartData.map((entry, index) => {
                  const val = (entry[diffKey] as number) || 0;
                  return (
                    <Cell
                      key={`cell-${index}`}
                      fill={
                        entry.isAnomaly
                          ? '#d32f2f' // Critical red for anomaly
                          : val >= 0
                          ? '#1a56c4' // Solid primary blue
                          : '#5b6472' // Dark slate gray
                      }
                    />
                  );
                })}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};
