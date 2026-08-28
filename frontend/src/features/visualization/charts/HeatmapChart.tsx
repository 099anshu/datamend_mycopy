'use client';

import React, { useMemo } from 'react';
import ReactECharts from 'echarts-for-react';
import { ChartPanel } from '@/shared/ui';
import { Flame } from 'lucide-react';
import { generateHeatmapGrid, ProcessedTimeSeriesPoint } from '@/lib/transforms';
import { createHeatmapOption } from './echarts/configFactory';

interface HeatmapChartProps {
  data: ProcessedTimeSeriesPoint[];
  columns: string[];
}

export const HeatmapChart: React.FC<HeatmapChartProps> = ({ data, columns }) => {
  const grid = useMemo(() => {
    return generateHeatmapGrid(data, columns, 36);
  }, [data, columns]);

  const option = useMemo(() => {
    return createHeatmapOption(grid.columns, grid.timeBuckets);
  }, [grid]);

  if (data.length === 0 || grid.columns.length === 0) return null;

  return (
    <ChartPanel
      title="Feature × Temporal Anomaly Heatmap"
      height={220}
      headerActions={
        <div className="flex items-center gap-2 text-[11px]">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-sm bg-slate-100 border border-slate-300" /> Normal
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-sm bg-orange-200" /> Elevated
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-sm bg-red-600" /> Anomaly (High)
          </span>
        </div>
      }
    >
      <div className="w-full h-full">
        <ReactECharts
          option={option}
          style={{ height: '100%', width: '100%' }}
          notMerge={true}
          lazyUpdate={true}
        />
      </div>
    </ChartPanel>
  );
};