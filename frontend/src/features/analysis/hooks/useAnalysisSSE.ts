import { useEffect, useRef, useCallback } from 'react';
import { AnalysisDetailResponse } from '../services/schemas';
import { getAnalysisDetailApi } from '../services/analysisApi';

export interface UseAnalysisSSEOptions {
  analysisId: string | null;
  onStatus?: (status: string) => void;
  onCompleted?: (response: AnalysisDetailResponse) => void;
  onError?: (error: string) => void;
}

export function useAnalysisSSE({
  analysisId,
  onStatus,
  onCompleted,
  onError,
}: UseAnalysisSSEOptions) {
  const isDoneRef = useRef(false);
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  const cleanup = useCallback(() => {
    isDoneRef.current = true;
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
  }, []);

  const startPollingFallback = useCallback(
    (id: string) => {
      if (pollIntervalRef.current || isDoneRef.current) return;
      pollIntervalRef.current = setInterval(async () => {
        try {
          const detail = await getAnalysisDetailApi(id);
          if (detail.status === 'COMPLETED') {
            cleanup();
            onCompleted?.(detail);
          } else if (detail.status === 'FAILED') {
            cleanup();
            onError?.('Analysis failed during execution');
          } else if (detail.status === 'RUNNING') {
            onStatus?.('RUNNING');
          }
        } catch (err: unknown) {
          const msg = err instanceof Error ? err.message : String(err);
          console.warn('Polling check error:', msg);
        }
      }, 1500);
    },
    [cleanup, onCompleted, onError, onStatus]
  );

  useEffect(() => {
    if (!analysisId) return;
    isDoneRef.current = false;

    const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
    if (typeof window !== 'undefined' && window.EventSource) {
      const url = `${API_BASE}/api/v1/analyses/${encodeURIComponent(analysisId)}/events`;
      const es = new EventSource(url);
      eventSourceRef.current = es;

      es.addEventListener('status', (e) => {
        try {
          const data = JSON.parse(e.data);
          onStatus?.(data.status || 'RUNNING');
        } catch {
          onStatus?.('RUNNING');
        }
      });

      es.addEventListener('completed', (e) => {
        cleanup();
        try {
          const response = JSON.parse(e.data) as AnalysisDetailResponse;
          onCompleted?.(response);
        } catch (err: unknown) {
          const message = err instanceof Error ? err.message : 'Unknown parsing error';
          onError?.(`Failed to parse analysis result: ${message}`);
        }
      });

      es.addEventListener('failed', (e) => {
        cleanup();
        try {
          const data = JSON.parse(e.data);
          onError?.(data.error || 'Analysis execution failed');
        } catch {
          onError?.('Analysis execution failed');
        }
      });

      es.onerror = () => {
        if (!isDoneRef.current) {
          if (eventSourceRef.current) {
            eventSourceRef.current.close();
            eventSourceRef.current = null;
          }
          startPollingFallback(analysisId);
        }
      };
    } else {
      startPollingFallback(analysisId);
    }

    return () => {
      cleanup();
    };
  }, [analysisId, cleanup, onCompleted, onError, onStatus, startPollingFallback]);
}
