import { useMemo } from 'react';
import { AnomalyItem, Severity, TimestampScore } from '@/types/api';
import { formatTimestamp, normalizeTimestampKey, ProcessedTimeSeriesPoint } from '@/lib/transforms';
import { useRollingWindow } from './useRollingWindow';

export function useTimeSeriesMerge(
  scores: TimestampScore[] | undefined,
  anomalies: AnomalyItem[] | undefined,
  columns: string[],
  rollingWindow: number = 0
): ProcessedTimeSeriesPoint[] {
  const mergedBase = useMemo(() => {
    if (!scores || scores.length === 0) return [];

    const anomalyMap = new Map<string, AnomalyItem[]>();
    (anomalies || []).forEach((a) => {
      const key = normalizeTimestampKey(a.timestamp);
      const list = anomalyMap.get(key) || [];
      list.push(a);
      anomalyMap.set(key, list);
    });

    const n = scores.length;
    const result: ProcessedTimeSeriesPoint[] = new Array(n);

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

      result[i] = {
        index: i,
        timestamp: item.timestamp,
        formattedTime: formatTimestamp(item.timestamp),
        score: Number(item.score.toFixed(4)),
        isAnomaly,
        anomalySeverity: highestSeverity,
        anomalyColumn: matchedAnomalies
          .map((a) => a.columnName || a.column || '')
          .filter(Boolean)
          .join(', '),
        ...item.values,
      };
    }

    return result;
  }, [scores, anomalies]);

  return useRollingWindow(mergedBase, columns, rollingWindow);
}
