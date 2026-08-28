import * as echarts from 'echarts/core';

export const ECHARTS_PALETTE = [
  '#1a56c4',
  '#059669',
  '#d97706',
  '#7c3aed',
  '#0284c7',
  '#db2777',
  '#4b5563',
];

export const HEATMAP_GRADIENT = [
  '#dcfce7',
  '#fef3c7',
  '#fee2e2',
];

echarts.registerTheme('datamend', {
  color: ECHARTS_PALETTE,
  backgroundColor: 'transparent',
  textStyle: {
    fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    color: '#1a1a1a',
    fontSize: 12,
  },
  title: {
    textStyle: {
      color: '#1a1a1a',
      fontWeight: 700,
      fontSize: 14,
    },
    subtextStyle: {
      color: '#5b6472',
      fontSize: 12,
    },
  },
  legend: {
    textStyle: {
      color: '#5b6472',
      fontSize: 11,
    },
    inactiveColor: '#cbd5e1',
    pageIconColor: '#1a56c4',
    pageIconInactiveColor: '#94a3b8',
    pageTextStyle: {
      color: '#5b6472',
    },
  },
  grid: {
    left: '3%',
    right: '4%',
    bottom: '3%',
    top: '8%',
    containLabel: true,
  },
  xAxis: {
    type: 'category',
    axisLine: {
      lineStyle: {
        color: '#d7dbe0',
      },
    },
    axisTick: {
      show: false,
    },
    axisLabel: {
      color: '#64748b',
      fontSize: 10,
      margin: 8,
    },
    splitLine: {
      show: false,
    },
    boundaryGap: false,
  },
  yAxis: {
    type: 'value',
    axisLine: {
      lineStyle: {
        color: '#d7dbe0',
      },
    },
    axisTick: {
      show: false,
    },
    axisLabel: {
      color: '#64748b',
      fontSize: 10,
      margin: 8,
    },
    splitLine: {
      show: true,
      lineStyle: {
        color: '#e2e8f0',
        type: 'dashed',
        width: 1,
      },
    },
  },
  polar: {},
  radar: {},
  angleAxis: {},
  radiusAxis: {},
  singleAxis: {},
  brush: {},
  geo: {},
  parallel: {},
  sankey: {},
  funnel: {},
  gauge: {},
  pictorialBar: {},
  themeRiver: {},
  sunburst: {},
  custom: {},
  tooltip: {
    show: true,
    trigger: 'axis',
    backgroundColor: '#ffffff',
    borderColor: '#d7dbe0',
    borderWidth: 1,
    borderRadius: 4,
    padding: [10, 12],
    textStyle: {
      color: '#1a1a1a',
      fontSize: 12,
      fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    },
    extraCssText: 'box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);',
    axisPointer: {
      type: 'cross',
      lineStyle: {
        color: '#94a3b8',
        width: 1,
        type: 'dashed',
      },
      crossStyle: {
        color: '#94a3b8',
        width: 1,
        type: 'dashed',
      },
      shadowStyle: {
        color: 'rgba(148, 163, 184, 0.1)',
      },
    },
  },
  toolbox: {
    iconStyle: {
      borderColor: '#1a56c4',
    },
    emphasis: {
      iconStyle: {
        borderColor: '#144296',
      },
    },
  },
  dataZoom: [
    {
      type: 'inside',
      filterMode: 'filter',
      xAxisIndex: [0],
      zoomOnMouseWheel: true,
      moveOnMouseMove: true,
      moveOnMouseWheel: false,
      preventDefaultMouseMove: true,
    },
    {
      type: 'slider',
      height: 20,
      bottom: 0,
      left: '3%',
      right: '4%',
      borderColor: '#d7dbe0',
      fillerColor: 'rgba(28, 75, 90, 0.15)',
      handleIcon:
        'M10.7,11.9H9.3c-4.9,0.3-8.8,4.4-8.8,9.4c0,5,3.9,9.1,8.8,9.4h1.3c4.9-0.3,8.8-4.4,8.8-9.4C19.5,16.3,15.6,12.2,10.7,11.9z M13.3,24.4H6.7v-1.2h6.6z M13.3,22H6.7v-1.2h6.6z M13.3,19.6H6.7v-1.2h6.6z',
      handleSize: '100%',
      handleStyle: {
        color: '#1c4b5a',
        borderWidth: 1,
        borderColor: '#1c4b5a',
      },
      textStyle: {
        color: '#5b6472',
      },
    },
  ],
  visualMap: {
    show: false,
    type: 'continuous',
    min: 0,
    max: 1,
    inRange: {
      color: HEATMAP_GRADIENT,
    },
    outOfRange: {
      color: ['#f1f5f9'],
    },
    textStyle: {
      color: '#5b6472',
    },
  },
  timeline: {},
  graphic: {},
  calendar: {},
  dataset: {},
  aria: {
    enabled: true,
    label: {
      general: {
        withName: 'Chart: {name}',
        withoutName: 'Chart',
      },
      series: {
        single: {
          prefix: '{name}: ',
          withName: '{name} - {seriesName}',
          withoutName: '{seriesName}',
        },
        multiple: {
          prefix: '{name}: ',
          withName: '{name} - {seriesName}',
          withoutName: '{seriesName}',
        },
      },
    },
  },
  series: {
    line: {
      sampling: 'lttb',
      progressive: 5000,
      progressiveThreshold: 3000,
      smooth: true,
      symbol: 'none',
      lineStyle: {
        width: 1.5,
      },
      emphasis: {
        focus: 'series',
        lineStyle: {
          width: 2.5,
        },
      },
    },
    area: {
      sampling: 'lttb',
      progressive: 5000,
      progressiveThreshold: 3000,
      emphasis: {
        focus: 'series',
      },
    },
    bar: {
      emphasis: {
        focus: 'series',
        itemStyle: {
          shadowBlur: 10,
          shadowColor: 'rgba(0, 0, 0, 0.2)',
        },
      },
    },
    heatmap: {
      emphasis: {
        focus: 'cell',
        itemStyle: {
          shadowBlur: 10,
          shadowColor: 'rgba(0, 0, 0, 0.5)',
        },
      },
    },
    scatter: {
      sampling: 'lttb',
    },
  },
});

export type DatamendTheme = typeof import('echarts').registerTheme extends (name: string, theme: infer T) => void ? T : never;