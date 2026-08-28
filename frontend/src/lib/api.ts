import {
  AnalysisDetailResponse,
  AnalysisJobResponse,
  AnalysisRequestPayload,
  ScoresResponse,
} from '@/types/api';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';

// In-flight promise cache for request deduplication
const inFlightRequests = new Map<string, Promise<unknown>>();
// Simple LRU/TTL Cache for static scores queries
const cache = new Map<string, { data: unknown; expiry: number }>();
const CACHE_TTL_MS = 30000;

async function fetchWithRetry<T>(
  url: string,
  options: RequestInit,
  retries: number = 2,
  backoffMs: number = 500
): Promise<T> {
  const cacheKey = `${options.method || 'GET'}:${url}:${options.body ? String(options.body) : ''}`;

  // Check TTL cache for GET/Scores
  if ((!options.method || options.method === 'GET' || url.includes('/scores')) && cache.has(cacheKey)) {
    const entry = cache.get(cacheKey)!;
    if (Date.now() < entry.expiry) {
      return entry.data as T;
    }
    cache.delete(cacheKey);
  }

  // Deduplicate in-flight requests
  if (inFlightRequests.has(cacheKey)) {
    return inFlightRequests.get(cacheKey) as Promise<T>;
  }

  const promise = (async () => {
    let lastError: unknown;
    for (let attempt = 0; attempt <= retries; attempt++) {
      try {
        const res = await fetch(url, options);
        if (!res.ok) {
          const errorBody = await res.json().catch(() => ({}));
          const message =
            errorBody.detail || errorBody.error || `HTTP ${res.status}: Request failed`;
          throw new Error(message);
        }
        const data = (await res.json()) as T;
        cache.set(cacheKey, { data, expiry: Date.now() + CACHE_TTL_MS });
        return data;
      } catch (err: unknown) {
        lastError = err;
        if (attempt < retries) {
          await new Promise((r) => setTimeout(r, backoffMs * Math.pow(2, attempt)));
        }
      }
    }
    throw lastError instanceof Error ? lastError : new Error(String(lastError));
  })();

  inFlightRequests.set(cacheKey, promise);
  try {
    return await promise;
  } finally {
    inFlightRequests.delete(cacheKey);
  }
}

export async function fetchScores(payload: AnalysisRequestPayload): Promise<ScoresResponse> {
  return fetchWithRetry<ScoresResponse>(`${API_BASE}/api/v1/ml/scores`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export async function startAnalysis(payload: AnalysisRequestPayload): Promise<AnalysisJobResponse> {
  return fetchWithRetry<AnalysisJobResponse>(
    `${API_BASE}/api/v1/ml/analyze`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    },
    0 // No retries for triggering jobs to avoid duplicate execution
  );
}

export async function getAnalysisDetail(analysisId: string): Promise<AnalysisDetailResponse> {
  return fetchWithRetry<AnalysisDetailResponse>(
    `${API_BASE}/api/v1/analyses/${encodeURIComponent(analysisId)}`,
    {
      method: 'GET',
      headers: { Accept: 'application/json' },
    }
  );
}

export interface AnalysisEventCallbacks {
  onStatus?: (status: string) => void;
  onCompleted?: (response: AnalysisDetailResponse) => void;
  onError?: (error: string) => void;
}

export function subscribeToAnalysisEvents(
  analysisId: string,
  callbacks: AnalysisEventCallbacks
): () => void {
  let isDone = false;
  let pollInterval: ReturnType<typeof setInterval> | null = null;
  let eventSource: EventSource | null = null;

  const startPollingFallback = () => {
    if (pollInterval || isDone) return;
    pollInterval = setInterval(async () => {
      try {
        const detail = await getAnalysisDetail(analysisId);
        if (detail.status === 'COMPLETED') {
          isDone = true;
          if (pollInterval) clearInterval(pollInterval);
          callbacks.onCompleted?.(detail);
        } else if (detail.status === 'FAILED') {
          isDone = true;
          if (pollInterval) clearInterval(pollInterval);
          callbacks.onError?.('Analysis failed during execution');
        } else if (detail.status === 'RUNNING') {
          callbacks.onStatus?.('RUNNING');
        }
      } catch (err: unknown) {
        const errorMsg = err instanceof Error ? err.message : String(err);
        console.warn('Polling check error:', errorMsg);
      }
    }, 1500);
  };

  if (typeof window !== 'undefined' && window.EventSource) {
    const url = `${API_BASE}/api/v1/analyses/${encodeURIComponent(analysisId)}/events`;
    eventSource = new EventSource(url);

    eventSource.addEventListener('status', (e) => {
      try {
        const data = JSON.parse(e.data);
        callbacks.onStatus?.(data.status || 'RUNNING');
      } catch {
        callbacks.onStatus?.('RUNNING');
      }
    });

    eventSource.addEventListener('completed', (e) => {
      isDone = true;
      if (eventSource) eventSource.close();
      try {
        const response = JSON.parse(e.data) as AnalysisDetailResponse;
        callbacks.onCompleted?.(response);
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : 'Unknown parsing error';
        callbacks.onError?.(`Failed to parse analysis result: ${message}`);
      }
    });

    eventSource.addEventListener('failed', (e) => {
      isDone = true;
      if (eventSource) eventSource.close();
      try {
        const data = JSON.parse(e.data);
        callbacks.onError?.(data.error || 'Analysis execution failed');
      } catch {
        callbacks.onError?.('Analysis execution failed');
      }
    });

    eventSource.onerror = () => {
      if (!isDone) {
        if (eventSource) eventSource.close();
        startPollingFallback();
      }
    };
  } else {
    startPollingFallback();
  }

  return () => {
    isDone = true;
    if (eventSource) eventSource.close();
    if (pollInterval) clearInterval(pollInterval);
  };
}
