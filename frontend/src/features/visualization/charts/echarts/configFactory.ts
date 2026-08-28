import type { EChartsOption } from 'echarts';
import { ProcessedTimeSeriesPoint, HeatmapCell } from '@/lib/transforms';

export const ECHARTS_PALETTE = [
  '#1a56c4', // Blue
  '#059669', // Emerald
  '#d97706', // Amber
  '#7c3aed', // Purple
  '#0284c7', // Sky
  '#db2777', // Rose
  '#4b5563', // Slate
];

export const HEATMAP_GRADIENT = [
  '#f1f5f9', // Normal
  '#dbeafe', // Low Elevated
  '#fed7aa', // Moderate
  '#fb923c', // High Score
  '#d32f2f', // Critical Anomaly
];

export const createBaseOption = (): Partial<EChartsOption> => ({
  color: ECHARTS_PALETTE,
  backgroundColor: 'transparent',
  animationDuration: 200,
  animationEasing: 'cubicOut',
  grid: {
    top: 24,
    right: 16,
    bottom: 36,
    left: 48,
    containLabel: false,
  },
  dataZoom: [
    {
      type: 'inside',
      filterMode: 'filter',
    },
    {
      type: 'slider',
      height: 18,
      bottom: 2,
      borderColor: '#d7dbe0',
      fillerColor: 'rgba(28, 75, 90, 0.15)',
      handleSize: '100%',
      handleStyle: {
        color: '#1c4b5a',
      },
      textStyle: {
        fontSize: 10,
        color: '#64748b',
      },
    },
  ],
});

export const createTimeSeriesOption = (
  data: ProcessedTimeSeriesPoint[],
  columns: string[],
  showRolling: boolean = false,
  rollingWindow: number = 24
): EChartsOption => {
  const timestamps = data.map((d) => d.formattedTime);
  const seriesList: EChartsOption['series'] = [];

  columns.forEach((col, idx) => {
    const color = ECHARTS_PALETTE[idx % ECHARTS_PALETTE.length];
    // Main signal line
    seriesList.push({
      name: col,
      type: 'line',
      data: data.map((d) => (d[col] !== undefined ? (d[col] as number) : null)),
      showSymbol: false,
      sampling: 'lttb',
      lineStyle: { width: 1.5, color },
      itemStyle: { color },
    });

    // Rolling average line
    if (showRolling) {
      seriesList.push({
        name: `${col} (SMA ${rollingWindow})`,
        type: 'line',
        data: data.map((d) => (d[`${col}_rolling`] !== undefined ? (d[`${col}_rolling`] as number) : null)),
        showSymbol: false,
        sampling: 'lttb',
        lineStyle: { width: 1.5, color, type: 'dashed', opacity: 0.7 },
        itemStyle: { color },
      });
    }
  });

  return {
    ...createBaseOption(),
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#ffffff',
      borderColor: '#d7dbe0',
      borderWidth: 1,
      textStyle: { color: '#1a1a1a', fontSize: 11 },
      padding: [8, 10],
      axisPointer: {
        type: 'cross',
        lineStyle: { color: '#94a3b8', type: 'dashed' },
      },
    },
    xAxis: {
      type: 'category',
      data: timestamps,
      boundaryGap: false,
      axisLine: { lineStyle: { color: '#d7dbe0' } },
      axisLabel: { color: '#64748b', fontSize: 10 },
      splitLine: { show: true, lineStyle: { color: '#e2e8f0', type: 'dashed' } },
    },
    yAxis: {
      type: 'value',
      scale: true,
      axisLine: { show: false },
      axisLabel: { color: '#64748b', fontSize: 10 },
      splitLine: { lineStyle: { color: '#e2e8f0', type: 'dashed' } },
    },
    series: seriesList,
  };
};

export const createScoreCurveOption = (
  data: ProcessedTimeSeriesPoint[],
  threshold: number
): EChartsOption => {
  const timestamps = data.map((d) => d.formattedTime);
  const scores = data.map((d) => d.score);

  return {
    ...createBaseOption(),
    grid: {
      top: 20,
      right: 16,
      bottom: 32,
      left: 44,
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#ffffff',
      borderColor: '#d7dbe0',
      padding: [6, 10],
      textStyle: { color: '#1a1a1a', fontSize: 11 },
      axisPointer: {
        type: 'cross',
        lineStyle: { color: '#94a3b8', type: 'dashed' },
      },
    },
    xAxis: {
      type: 'category',
      data: timestamps,
      boundaryGap: false,
      axisLine: { lineStyle: { color: '#d7dbe0' } },
      axisLabel: { color: '#64748b', fontSize: 10 },
      splitLine: { show: true, lineStyle: { color: '#e2e8f0', type: 'dashed' } },
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 1,
      interval: 0.25,
      axisLabel: { color: '#64748b', fontSize: 10 },
      splitLine: { lineStyle: { color: '#e2e8f0', type: 'dashed' } },
    },
    series: [
      {
        name: 'Anomaly Score',
        type: 'line',
        data: scores,
        showSymbol: false,
        sampling: 'lttb',
        lineStyle: { width: 1.5, color: '#1a56c4' },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(211, 47, 47, 0.3)' },
              { offset: 1, color: 'rgba(26, 86, 196, 0.04)' },
            ],
          },
        },
        markLine: {
          symbol: 'none',
          silent: true,
          lineStyle: { color: '#d32f2f', type: 'dashed', width: 1.5 },
          data: [{ yAxis: threshold, label: { formatter: `Cutoff ${threshold.toFixed(2)}`, position: 'insideEndTop', color: '#d32f2f', fontSize: 10, fontWeight: 'bold' } }],
        },
      },
    ],
  };
};

export const createBaselineDeviationOption = (
  data: ProcessedTimeSeriesPoint[],
  column: string
): EChartsOption => {
  const diffKey = `${column}_diff`;
  const timestamps = data.map((d) => d.formattedTime);
  const diffValues = data.map((d) => (typeof d[diffKey] === 'number' ? (d[diffKey] as number) : 0));

  return {
    ...createBaseOption(),
    grid: {
      top: 20,
      right: 16,
      bottom: 32,
      left: 44,
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#ffffff',
      borderColor: '#d7dbe0',
      padding: [6, 10],
      textStyle: { color: '#1a1a1a', fontSize: 11 },
      axisPointer: {
        type: 'shadow',
      },
    },
    xAxis: {
      type: 'category',
      data: timestamps,
      axisLine: { lineStyle: { color: '#d7dbe0' } },
      axisLabel: { color: '#64748b', fontSize: 10 },
      splitLine: { show: false },
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: '#64748b', fontSize: 10 },
      splitLine: { lineStyle: { color: '#e2e8f0', type: 'dashed' } },
    },
    series: [
      {
        name: `Delta (${column})`,
        type: 'bar',
        data: diffValues.map((val, idx) => ({
          value: val,
          itemStyle: {
            color: data[idx]?.isAnomaly ? '#d32f2f' : val >= 0 ? '#1a56c4' : '#5b6472',
          },
        })),
        sampling: 'lttb',
        barMaxWidth: 8,
      },
    ],
  };
};

export const createHeatmapOption = (
  columns: string[],
  timeBuckets: { label: string; cells: HeatmapCell[] }[]
): EChartsOption => {
  const timeLabels = timeBuckets.map((b) => b.label);
  const matrixData: [number, number, number][] = [];

  timeBuckets.forEach((bucket, tIdx) => {
    bucket.cells.forEach((cell) => {
      const cIdx = columns.indexOf(cell.column);
      if (cIdx >= 0) {
        matrixData.push([tIdx, cIdx, Number(cell.score.toFixed(3))]);
      }
    });
  });

  return {
    backgroundColor: 'transparent',
    tooltip: {
      position: 'top',
      backgroundColor: '#ffffff',
      borderColor: '#d7dbe0',
      padding: [6, 10],
      textStyle: { color: '#1a1a1a', fontSize: 11 },
      formatter: (params: unknown) => {
        const item = params as { data: [number, number, number] };
        if (!item || !item.data) return '';
        const [tIdx, cIdx, score] = item.data;
        const timeLabel = timeLabels[tIdx] || '';
        const col = columns[cIdx] || '';
        return `
          <div style="font-weight:700;">${timeLabel}</div>
          <div>Channel: <strong>${col}</strong></div>
          <div>Anomaly Score: <strong>${score}</strong></div>
        `;
      },
    },
    grid: {
      top: 10,
      right: 16,
      bottom: 24,
      left: 54,
    },
    xAxis: {
      type: 'category',
      data: timeLabels,
      splitArea: { show: false },
      axisLabel: { color: '#64748b', fontSize: 10 },
      axisLine: { lineStyle: { color: '#d7dbe0' } },
    },
    yAxis: {
      type: 'category',
      data: columns,
      inverse: true,
      splitArea: { show: false },
      axisLabel: { color: '#64748b', fontSize: 10, fontWeight: 'bold' },
      axisLine: { lineStyle: { color: '#d7dbe0' } },
    },
    visualMap: {
      min: 0,
      max: 1,
      calculable: false,
      orient: 'horizontal',
      left: 'center',
      bottom: 0,
      show: false,
      inRange: {
        color: HEATMAP_GRADIENT,
      },
    },
    series: [
      {
        name: 'Heatmap',
        type: 'heatmap',
        data: matrixData,
        label: { show: false },
        emphasis: {
          itemStyle: {
            shadowBlur: 8,
            shadowColor: 'rgba(0, 0, 0, 0.25)',
          },
        },
      },
    ],
  };
};