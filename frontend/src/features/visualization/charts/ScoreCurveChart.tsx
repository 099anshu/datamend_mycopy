'use client';

import React, { useMemo, useRef, useEffect } from 'react';
import ReactECharts from 'echarts-for-react';
import type EChartsReact from 'echarts-for-react';
import { ChartPanel } from '@/shared/ui';
import { ShieldAlert } from 'lucide-react';
import { ProcessedTimeSeriesPoint } from '@/lib/transforms';
import { createScoreCurveOption } from './echarts/configFactory';

interface ScoreCurveChartProps {
  data: ProcessedTimeSeriesPoint[];
  threshold: number;
  syncGroupId?: string;
}

export const ScoreCurveChart: React.FC<ScoreCurveChartProps> = ({
  data,
  threshold,
  syncGroupId,
}) => {
  const chartRef = useRef<EChartsReact>(null);

  useEffect(() => {
    if (chartRef.current && syncGroupId) {
      const echartInstance = chartRef.current.getEchartsInstance();
      echartInstance.group = syncGroupId;
    }
  }, [syncGroupId]);

  const option = useMemo(() => {
    return createScoreCurveOption(data, threshold);
  }, [data, threshold]);

  if (data.length === 0) return null;

  return (
    <ChartPanel
      title="TimeRCD Score Curve & Decision Boundary"
      height={220}
      headerActions={
        <span className="bg-white/20 text-white px-2 py-0.5 rounded text-[11px] font-bold">
          CUTOFF: <span className="tabular-nums">{threshold.toFixed(2)}</span>
        </span>
      }
    >
      <div className="w-full h-full">
        <ReactECharts
          ref={chartRef}
          option={option}
          style={{ height: '100%', width: '100%' }}
          notMerge={true}
          lazyUpdate={true}
        />
      </div>
    </ChartPanel>
  );
};