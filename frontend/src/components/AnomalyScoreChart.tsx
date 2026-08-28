'use client';

import React from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
  CartesianGrid,
} from 'recharts';
import { ShieldAlert } from 'lucide-react';
import { ProcessedTimeSeriesPoint } from '@/lib/transforms';

interface AnomalyScoreChartProps {
  data: ProcessedTimeSeriesPoint[];
  threshold: number;
}

export const AnomalyScoreChart: React.FC<AnomalyScoreChartProps> = ({ data, threshold }) => {
  if (data.length === 0) return null;

  return (
    <div className="panel">
      {/* Edge-to-edge Header Bar */}
      <div className="panel-header">
        <div className="panel-header-title">
          <span>TimeRCD Score Curve &amp; Decision Boundary</span>
        </div>
        <span
          style={{
            backgroundColor: 'rgba(255, 255, 255, 0.15)',
            color: '#ffffff',
            padding: '2px 8px',
            borderRadius: 3,
            fontSize: '0.6875rem',
            fontWeight: 700,
          }}
        >
          CUTOFF: <span className="tabular-nums">{threshold.toFixed(2)}</span>
        </span>
      </div>

      <div className="panel-body">
        <div style={{ width: '100%', height: 200 }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 8, right: 16, left: -10, bottom: 0 }}>
              <defs>
                <linearGradient id="scoreLightGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#d32f2f" stopOpacity={0.25} />
                  <stop offset="95%" stopColor="#1a56c4" stopOpacity={0.05} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis
                dataKey="formattedTime"
                stroke="#64748b"
                fontSize={10}
                tickLine={false}
                interval="preserveStartEnd"
                minTickGap={40}
              />
              <YAxis
                stroke="#64748b"
                fontSize={10}
                tickLine={false}
                domain={[0, 1]}
                ticks={[0, 0.25, 0.5, 0.75, 1.0]}
              />
              <Tooltip
                content={({ active, payload }) => {
                  if (!active || !payload || !payload.length) return null;
                  const pt = payload[0].payload as ProcessedTimeSeriesPoint;
                  const isAbove = pt.score >= threshold;
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
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <span style={{ fontWeight: 600 }}>Score:</span>
                        <strong
                          className="tabular-nums"
                          style={{ color: isAbove ? 'var(--status-critical)' : 'var(--accent)', fontSize: '0.875rem' }}
                        >
                          {pt.score.toFixed(4)}
                        </strong>
                      </div>
                      {isAbove && (
                        <div style={{ marginTop: 4 }}>
                          <span className="chip chip-critical">ANOMALY TRIGGERED</span>
                        </div>
                      )}
                    </div>
                  );
                }}
              />
              <ReferenceLine
                y={threshold}
                stroke="#d32f2f"
                strokeDasharray="4 4"
                strokeWidth={1.5}
                label={{
                  value: `Threshold ${threshold.toFixed(2)}`,
                  fill: '#d32f2f',
                  fontSize: 10,
                  fontWeight: 700,
                  position: 'insideTopRight',
                }}
              />
              <Area
                type="monotone"
                dataKey="score"
                stroke="#1a56c4"
                strokeWidth={1.5}
                fillOpacity={1}
                fill="url(#scoreLightGradient)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};
