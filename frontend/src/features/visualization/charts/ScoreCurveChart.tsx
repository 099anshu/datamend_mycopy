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
  onChartRef?: (chart: EChartsReact | null) => void;
  onDataZoom?: (params: { start?: number; end?: number }, chart: EChartsReact) => void;
}

export const ScoreCurveChart: React.FC<ScoreCurveChartProps> = ({
  data,
  threshold,
  onChartRef,
  onDataZoom,
}) => {
  const chartRef = useRef<EChartsReact>(null);

  useEffect(() => {
    if (chartRef.current && onChartRef) {
      onChartRef(chartRef.current);
    }
    return () => {
      if (onChartRef) onChartRef(null);
    };
  }, [onChartRef]);

  const option = useMemo(() => {
    return createScoreCurveOption(data, threshold);
  }, [data, threshold]);

  const onEvents = useMemo(() => {
    return {
      datazoom: (params: { start?: number; end?: number }) => {
        if (chartRef.current && onDataZoom) {
          onDataZoom(params, chartRef.current);
        }
      },
    };
  }, [onDataZoom]);

  if (data.length === 0) return null;

  return (
    <ChartPanel
      title="TimeRCD Score Curve & Decision Boundary"
      icon={<ShieldAlert size={16} />}
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
          onEvents={onEvents}
          style={{ height: '100%', width: '100%' }}
          notMerge={true}
          lazyUpdate={true}
        />
      </div>
    </ChartPanel>
  );
};