'use client';

import React, { useState, useEffect, useMemo, useRef } from 'react';
import ReactECharts from 'echarts-for-react';
import type EChartsReact from 'echarts-for-react';
import { ChartPanel } from '@/shared/ui';
import { Layers, Eye, SlidersHorizontal } from 'lucide-react';
import { ProcessedTimeSeriesPoint } from '@/lib/transforms';
import { createTimeSeriesOption, ECHARTS_PALETTE } from './echarts/configFactory';

interface TimeSeriesChartProps {
  data: ProcessedTimeSeriesPoint[];
  columns: string[];
  rollingWindow: number;
  onRollingWindowChange: (w: number) => void;
  showRolling: boolean;
  onToggleRolling: () => void;
  showAnomaliesOnly: boolean;
  onToggleAnomaliesOnly: () => void;
  syncGroupId?: string;
}

export const TimeSeriesChart: React.FC<TimeSeriesChartProps> = ({
  data,
  columns,
  rollingWindow,
  onRollingWindowChange,
  showRolling,
  onToggleRolling,
  showAnomaliesOnly,
  onToggleAnomaliesOnly,
  syncGroupId,
}) => {
  const chartRef = useRef<EChartsReact>(null);
  const [activeColumns, setActiveColumns] = useState<string[]>(columns);

  useEffect(() => {
    setActiveColumns(columns);
  }, [columns]);

  useEffect(() => {
    if (chartRef.current && syncGroupId) {
      const echartInstance = chartRef.current.getEchartsInstance();
      echartInstance.group = syncGroupId;
    }
  }, [syncGroupId]);

  const toggleColumn = (col: string) => {
    setActiveColumns((prev) =>
      prev.includes(col) ? prev.filter((c) => c !== col) : [...prev, col]
    );
  };

  const chartData = useMemo(() => {
    if (!showAnomaliesOnly) return data;
    return data.filter((d) => d.isAnomaly);
  }, [data, showAnomaliesOnly]);

  const option = useMemo(() => {
    return createTimeSeriesOption(chartData, activeColumns, showRolling, rollingWindow);
  }, [chartData, activeColumns, showRolling, rollingWindow]);

  const status = data.length === 0 ? 'empty' : 'ready';

  return (
    <ChartPanel
      title="Multivariate Time-Series & Anomaly Overlay"
      height={360}
      status={status}
      headerActions={
         <div className="flex flex-wrap items-center gap-1.5 justify-end min-w-0">
          <button
            type="button"
            className={`btn btn-secondary ${showRolling ? 'bg-slate-100 border-slate-400' : ''}`}
            onClick={onToggleRolling}
            style={{ padding: '2px 6px', fontSize: '11px' }}
          >
            <SlidersHorizontal size={12} />
            SMA ({rollingWindow})
          </button>

          {showRolling && (
            <select
              className="form-select tabular-nums w-auto py-0.5 px-1.5 text-[11px]"
              value={rollingWindow}
              onChange={(e) => onRollingWindowChange(parseInt(e.target.value, 10))}
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
            className={`btn btn-secondary ${
              showAnomaliesOnly ? 'bg-red-50 text-red-700 border-red-300' : ''
            }`}
            onClick={onToggleAnomaliesOnly}
            style={{ padding: '2px 6px', fontSize: '11px' }}
          >
            <Eye size={12} />
            {showAnomaliesOnly ? 'Anomalies Only' : 'All Data'}
          </button>
        </div>
      }
    >
      <div className="flex flex-col gap-2 h-full">
        {/* Signal Channel Toggles */}
        <div className="flex flex-wrap gap-1 items-center pb-1">
          <span className="text-[11px] text-slate-500 uppercase font-semibold mr-1">
            Channels:
          </span>
          {columns.map((col, idx) => {
            const color = ECHARTS_PALETTE[idx % ECHARTS_PALETTE.length];
            const isVisible = activeColumns.includes(col);
            return (
              <button
                key={col}
                type="button"
                onClick={() => toggleColumn(col)}
                className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[11px] font-bold border transition-colors ${
                  isVisible ? 'bg-white text-slate-800' : 'bg-slate-50 text-slate-400 border-slate-200'
                }`}
                style={{ borderColor: isVisible ? color : undefined }}
              >
                <span
                  className="w-1.5 h-1.5 rounded-full"
                  style={{ backgroundColor: isVisible ? color : '#cbd5e1' }}
                />
                {col}
              </button>
            );
          })}
        </div>

        {/* ECharts Instance */}
        <div className="flex-1 w-full min-h-[300px]">
          <ReactECharts
            ref={chartRef}
            option={option}
            style={{ height: '100%', width: '100%' }}
            notMerge={true}
            lazyUpdate={true}
          />
        </div>
      </div>
    </ChartPanel>
  );
};