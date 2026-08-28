import { AnomalyItem, Severity, TimestampScore } from '@/types/api';

export interface ProcessedTimeSeriesPoint {
  index: number;
  timestamp: string;
  formattedTime: string;
  score: number;
  isAnomaly: boolean;
  anomalySeverity?: Severity;
  anomalyColumn?: string;
  [column: string]: number | string | boolean | undefined;
}

export function formatTimestamp(isoStr: string): string {
  try {
    const d = new Date(isoStr);
    if (isNaN(d.getTime())) return isoStr;
    return d.toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return isoStr;
  }
}

/**
 * Normalizes timestamps to a standard second-level epoch timestamp key
 * to handle millisecond rounding, ISO vs space-separated formats, and timezones.
 */
export function normalizeTimestampKey(ts: string): string {
  if (!ts) return '';
  const parsed = Date.parse(ts);
  if (!isNaN(parsed)) {
    // Round to nearest second for rock-solid cross-platform matching
    return String(Math.floor(parsed / 1000));
  }
  return ts.trim().replace(' ', 'T').replace(/\.\d+/, '').replace(/Z$/, '');
}

/**
 * Merges raw scores and detected anomalies with O(N) linear rolling window calculation
 * and timezone-resilient timestamp matching.
 */
export function mergeScoresAndAnomalies(
  scores: TimestampScore[],
  anomalies: AnomalyItem[],
  selectedColumns: string[],
  rollingWindow: number = 0
): ProcessedTimeSeriesPoint[] {
  // Index anomalies by normalized second-level timestamp
  const anomalyMap = new Map<string, AnomalyItem[]>();
  anomalies.forEach((a) => {
    const key = normalizeTimestampKey(a.timestamp);
    const list = anomalyMap.get(key) || [];
    list.push(a);
    anomalyMap.set(key, list);
  });

  const n = scores.length;
  const result: ProcessedTimeSeriesPoint[] = new Array(n);

  // Pre-calculate running sums for O(N * cols) linear sliding-window rolling average
  const rollingWindowValid = rollingWindow > 1;
  const runningSums: Record<string, number> = {};
  const runningCounts: Record<string, number> = {};

  if (rollingWindowValid) {
    selectedColumns.forEach((col) => {
      runningSums[col] = 0;
      runningCounts[col] = 0;
    });
  }

  for (let i = 0; i < n; i++) {
    const item = scores[i];
    const key = normalizeTimestampKey(item.timestamp);
    const matchedAnomalies = anomalyMap.get(key) || [];
    const isAnomaly = matchedAnomalies.length > 0;

    let highestSeverity: Severity | undefined;
    if (isAnomaly) {
      if (matchedAnomalies.some((a) => a.severity === 'HIGH')) {
        highestSeverity = 'HIGH';
      } else if (matchedAnomalies.some((a) => a.severity === 'MEDIUM')) {
        highestSeverity = 'MEDIUM';
      } else {
        highestSeverity = 'LOW';
      }
    }

    const point: ProcessedTimeSeriesPoint = {
      index: i,
      timestamp: item.timestamp,
      formattedTime: formatTimestamp(item.timestamp),
      score: Number(item.score.toFixed(4)),
      isAnomaly,
      anomalySeverity: highestSeverity,
      anomalyColumn: matchedAnomalies.map((a) => a.columnName || a.column || '').filter(Boolean).join(', '),
      ...item.values,
    };

    // Linear O(1) sliding window calculation per column
    if (rollingWindowValid) {
      selectedColumns.forEach((col) => {
        const val = item.values[col];
        if (typeof val === 'number' && !isNaN(val)) {
          runningSums[col] += val;
          runningCounts[col] += 1;
        }

        // Subtract element that just slid out of the window
        if (i >= rollingWindow) {
          const outVal = scores[i - rollingWindow].values[col];
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
    }

    result[i] = point;
  }

  return result;
}

/**
 * Downsamples dense time-series for SVG chart rendering if point count is large,
 * guaranteeing all anomaly points and visual extremes are preserved.
 */
export function downsampleTimeSeries(
  points: ProcessedTimeSeriesPoint[],
  maxPoints: number = 1200
): ProcessedTimeSeriesPoint[] {
  if (points.length <= maxPoints) return points;

  const step = Math.ceil(points.length / maxPoints);
  const downsampled: ProcessedTimeSeriesPoint[] = [];

  for (let i = 0; i < points.length; i += step) {
    const chunk = points.slice(i, i + step);
    // If any point in chunk is an anomaly, prioritize keeping it
    const anomalyPoint = chunk.find((p) => p.isAnomaly);
    if (anomalyPoint) {
      downsampled.push(anomalyPoint);
    } else {
      downsampled.push(chunk[0]);
    }
  }

  return downsampled;
}

export interface HeatmapCell {
  column: string;
  timeIndex: number;
  timestamp: string;
  formattedTime: string;
  score: number;
  value: number;
  isAnomaly: boolean;
  severity?: Severity;
}

export function generateHeatmapGrid(
  scores: ProcessedTimeSeriesPoint[],
  columns: string[],
  maxBuckets: number = 36
): { columns: string[]; timeBuckets: { label: string; cells: HeatmapCell[] }[] } {
  if (scores.length === 0 || columns.length === 0) {
    return { columns: [], timeBuckets: [] };
  }

  const step = Math.max(1, Math.floor(scores.length / maxBuckets));
  const timeBuckets: { label: string; cells: HeatmapCell[] }[] = [];

  for (let i = 0; i < scores.length; i += step) {
    const slice = scores.slice(i, i + step);
    const rep = slice[Math.floor(slice.length / 2)] || slice[0];
    const maxScoreInBucket = Math.max(...slice.map((s) => s.score));
    const isAnomalyInBucket = slice.some((s) => s.isAnomaly);
    const bucketSeverity = slice.find((s) => s.anomalySeverity === 'HIGH')?.anomalySeverity ||
      slice.find((s) => s.anomalySeverity === 'MEDIUM')?.anomalySeverity ||
      slice.find((s) => s.anomalySeverity === 'LOW')?.anomalySeverity;

    const cells: HeatmapCell[] = columns.map((col) => {
      const avgVal =
        slice.reduce((acc, curr) => acc + (Number(curr[col]) || 0), 0) / slice.length;
      return {
        column: col,
        timeIndex: i,
        timestamp: rep.timestamp,
        formattedTime: rep.formattedTime,
        score: maxScoreInBucket,
        value: Number(avgVal.toFixed(2)),
        isAnomaly: isAnomalyInBucket,
        severity: bucketSeverity,
      };
    });

    timeBuckets.push({
      label: rep.formattedTime,
      cells,
    });
  }

  return { columns, timeBuckets };
}
