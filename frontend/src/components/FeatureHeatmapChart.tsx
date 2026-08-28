'use client';

import React, { useMemo } from 'react';
import { Flame } from 'lucide-react';
import { generateHeatmapGrid, ProcessedTimeSeriesPoint } from '@/lib/transforms';

interface FeatureHeatmapChartProps {
  data: ProcessedTimeSeriesPoint[];
  columns: string[];
}

export const FeatureHeatmapChart: React.FC<FeatureHeatmapChartProps> = ({ data, columns }) => {
  const grid = useMemo(() => {
    return generateHeatmapGrid(data, columns, 36);
  }, [data, columns]);

  if (data.length === 0 || grid.columns.length === 0) return null;

  const getCellColor = (score: number, isAnomaly: boolean, severity?: string) => {
    if (isAnomaly) {
      if (severity === 'HIGH') return '#d32f2f'; // Critical red
      if (severity === 'MEDIUM') return '#e69100'; // Warning orange
      return '#1a56c4'; // Info blue
    }
    if (score > 0.7) return '#fed7aa'; // light orange tint
    if (score > 0.4) return '#dbeafe'; // light blue tint
    return '#f1f5f9'; // baseline light slate
  };

  return (
    <div className="panel">
      {/* Edge-to-edge Header Bar */}
      <div className="panel-header">
        <div className="panel-header-title">
          <span>Feature × Temporal Anomaly Heatmap</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '0.6875rem' }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
            <span style={{ width: 8, height: 8, borderRadius: 2, backgroundColor: '#f1f5f9', border: '1px solid #cbd5e1' }} /> Normal
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
            <span style={{ width: 8, height: 8, borderRadius: 2, backgroundColor: '#fed7aa' }} /> Elevated
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
            <span style={{ width: 8, height: 8, borderRadius: 2, backgroundColor: '#d32f2f' }} /> Anomaly (High)
          </span>
        </div>
      </div>

      <div className="panel-body">
        <div style={{ overflowX: 'auto', paddingBottom: 4 }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4, minWidth: 600 }}>
            {grid.columns.map((col) => (
              <div key={col} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span
                  style={{
                    width: 54,
                    fontSize: '0.6875rem',
                    fontWeight: 700,
                    color: 'var(--text-secondary)',
                    textAlign: 'right',
                    flexShrink: 0,
                  }}
                >
                  {col}
                </span>

                <div style={{ display: 'flex', gap: 2, flex: 1 }}>
                  {grid.timeBuckets.map((bucket, bIdx) => {
                    const cell = bucket.cells.find((c) => c.column === col);
                    const bg = cell ? getCellColor(cell.score, cell.isAnomaly, cell.severity) : 'transparent';
                    return (
                      <div
                        key={bIdx}
                        title={`${bucket.label} | ${col}: avg ${cell?.value} | Score: ${cell?.score.toFixed(3)}${
                          cell?.isAnomaly ? ` (ANOMALY ${cell.severity})` : ''
                        }`}
                        style={{
                          flex: 1,
                          height: 18,
                          borderRadius: 2,
                          backgroundColor: bg,
                          border: cell?.isAnomaly ? '1px solid rgba(0,0,0,0.15)' : '1px solid #e2e8f0',
                          cursor: 'pointer',
                        }}
                      />
                    );
                  })}
                </div>
              </div>
            ))}

            {/* Time scale */}
            <div style={{ display: 'flex', marginLeft: 62, marginTop: 4, justifyContent: 'space-between', fontSize: '0.6875rem', color: 'var(--text-muted)' }}>
              <span>{grid.timeBuckets[0]?.label || ''}</span>
              <span>Sequence Timeline Progression →</span>
              <span>{grid.timeBuckets[grid.timeBuckets.length - 1]?.label || ''}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
