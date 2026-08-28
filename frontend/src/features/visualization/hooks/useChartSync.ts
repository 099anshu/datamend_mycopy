import { useCallback, useRef } from 'react';
import type EChartsReact from 'echarts-for-react';

export function useChartSync() {
  const chartRefs = useRef<(EChartsReact | null)[]>([]);
  const isSyncingRef = useRef(false);

  const registerChart = useCallback((chart: EChartsReact | null) => {
    if (chart && !chartRefs.current.includes(chart)) {
      chartRefs.current.push(chart);
    }
  }, []);

  const unregisterChart = useCallback((chart: EChartsReact | null) => {
    if (chart) {
      chartRefs.current = chartRefs.current.filter((c) => c !== chart);
    }
  }, []);

  const onDataZoom = useCallback((params: { start?: number; end?: number; batch?: { start?: number; end?: number }[] }, sourceChart: EChartsReact) => {
    if (isSyncingRef.current) return;
    isSyncingRef.current = true;

    let start = params.start;
    let end = params.end;
    if (params.batch && params.batch.length > 0) {
      start = params.batch[0].start;
      end = params.batch[0].end;
    }

    if (start !== undefined && end !== undefined) {
      chartRefs.current.forEach((ref) => {
        if (ref && ref !== sourceChart) {
          try {
            const instance = ref.getEchartsInstance();
            if (instance && !instance.isDisposed()) {
              instance.dispatchAction({
                type: 'dataZoom',
                start,
                end,
              });
            }
          } catch {
            // Ignore disposed instance actions
          }
        }
      });
    }

    setTimeout(() => {
      isSyncingRef.current = false;
    }, 50);
  }, []);

  return { registerChart, unregisterChart, onDataZoom };
}
