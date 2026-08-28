import { useMemo } from 'react';
import { ProcessedTimeSeriesPoint } from '@/lib/transforms';

/**
 * Calculates rolling average and diff using O(N * columns) sliding-window algorithm.
 */
export function useRollingWindow(
  data: ProcessedTimeSeriesPoint[],
  columns: string[],
  rollingWindow: number
): ProcessedTimeSeriesPoint[] {
  return useMemo(() => {
    if (rollingWindow <= 1 || data.length === 0 || columns.length === 0) {
      return data;
    }

    const n = data.length;
    const runningSums: Record<string, number> = {};
    const runningCounts: Record<string, number> = {};

    columns.forEach((col) => {
      runningSums[col] = 0;
      runningCounts[col] = 0;
    });

    const result: ProcessedTimeSeriesPoint[] = new Array(n);

    for (let i = 0; i < n; i++) {
      const item = data[i];
      const point: ProcessedTimeSeriesPoint = { ...item };

      columns.forEach((col) => {
        const val = item[col];
        if (typeof val === 'number' && !isNaN(val)) {
          runningSums[col] += val;
          runningCounts[col] += 1;
        }

        if (i >= rollingWindow) {
          const outVal = data[i - rollingWindow][col];
          if (typeof outVal === 'number' && !isNaN(outVal)) {
            runningSums[col] -= outVal;
            runningCounts[col] -= 1;
          }
        }

        const count = runningCounts[col];
        if (count > 0) {
          const avg = runningSums[col] / count;
          point[`${col}_rolling`] = Number(avg.toFixed(3));
          if (typeof val === 'number') {
            point[`${col}_diff`] = Number((val - avg).toFixed(3));
          }
        }
      });

      result[i] = point;
    }

    return result;
  }, [data, columns, rollingWindow]);
}
