'use client';

import React, { useState, useEffect, useMemo, useRef } from 'react';
import ReactECharts from 'echarts-for-react';
import type EChartsReact from 'echarts-for-react';
import { ChartPanel } from '@/shared/ui';
import { Compass } from 'lucide-react';
import { ProcessedTimeSeriesPoint } from '@/lib/transforms';
import { createBaselineDeviationOption } from './echarts/configFactory';

interface BaselineDeviationChartProps {
  data: ProcessedTimeSeriesPoint[];
  columns: string[];
  rollingWindow: number;
  onChartRef?: (chart: EChartsReact | null) => void;
  onDataZoom?: (params: { start?: number; end?: number }, chart: EChartsReact) => void;
}

export const BaselineDeviationChart: React.FC<BaselineDeviationChartProps> = ({
  data,
  columns,
  rollingWindow,
  onChartRef,
  onDataZoom,
}) => {
  const chartRef = useRef<EChartsReact>(null);
  const [selectedColumn, setSelectedColumn] = useState<string>(columns[0] || 'OT');

  useEffect(() => {
    if (columns.length > 0 && !columns.includes(selectedColumn)) {
      setSelectedColumn(columns[0]);
    }
  }, [columns, selectedColumn]);

  useEffect(() => {
    if (chartRef.current && onChartRef) {
      onChartRef(chartRef.current);
    }
    return () => {
      if (onChartRef) onChartRef(null);
    };
  }, [onChartRef]);

  const option = useMemo(() => {
    return createBaselineDeviationOption(data, selectedColumn);
  }, [data, selectedColumn]);

  const onEvents = useMemo(() => {
    return {
      datazoom: (params: { start?: number; end?: number }) => {
        if (chartRef.current && onDataZoom) {
          onDataZoom(params, chartRef.current);
        }
      },
    };
  }, [onDataZoom]);

  if (data.length === 0 || columns.length === 0) return null;

  return (
    <ChartPanel
      title="Actual vs. Baseline Deviation (Observable)"
      subtitle={`True vertical delta against ${rollingWindow}-step SMA baseline`}
      icon={<Compass size={16} />}
      height={220}
      headerActions={
        <div className="flex items-center gap-1.5">
          <span className="text-[11px] text-slate-300 uppercase font-semibold">Channel:</span>
          <select
            className="form-select w-auto py-0.5 px-2 text-[11px] bg-white text-slate-900"
            value={selectedColumn}
            onChange={(e) => setSelectedColumn(e.target.value)}
          >
            {columns.map((col) => (
              <option key={col} value={col}>
                {col}
              </option>
            ))}
          </select>
        </div>
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