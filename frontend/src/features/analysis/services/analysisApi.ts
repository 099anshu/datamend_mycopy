import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  AnalysisDetailResponse,
  AnalysisDetailResponseSchema,
  AnalysisJobResponse,
  AnalysisJobResponseSchema,
  AnalysisRequestPayload,
  ScoresResponse,
  ScoresResponseSchema,
} from './schemas';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';

export async function fetchScoresApi(payload: AnalysisRequestPayload): Promise<ScoresResponse> {
  const res = await fetch(`${API_BASE}/api/v1/ml/scores`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || err.error || `HTTP ${res.status}: Failed to fetch scores`);
  }

  const json = await res.json();
  return ScoresResponseSchema.parse(json);
}

export async function startAnalysisApi(payload: AnalysisRequestPayload): Promise<AnalysisJobResponse> {
  const res = await fetch(`${API_BASE}/api/v1/ml/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || err.error || `HTTP ${res.status}: Failed to start analysis`);
  }

  const json = await res.json();
  return AnalysisJobResponseSchema.parse(json);
}

export async function getAnalysisDetailApi(id: string): Promise<AnalysisDetailResponse> {
  const res = await fetch(`${API_BASE}/api/v1/analyses/${encodeURIComponent(id)}`, {
    method: 'GET',
    headers: { Accept: 'application/json' },
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `HTTP ${res.status}: Failed to fetch analysis detail`);
  }

  const json = await res.json();
  return AnalysisDetailResponseSchema.parse(json);
}

export function useScoresQuery(payload: AnalysisRequestPayload | null, enabled: boolean = false) {
  return useQuery({
    queryKey: ['scores', payload?.datasetName, payload?.columns?.join(','), payload?.detector],
    queryFn: () => (payload ? fetchScoresApi(payload) : Promise.reject('No payload')),
    enabled: enabled && !!payload,
    staleTime: 30000,
  });
}

export function useAnalysisDetailQuery(id: string | null) {
  return useQuery({
    queryKey: ['analysis', id],
    queryFn: () => (id ? getAnalysisDetailApi(id) : Promise.reject('No ID')),
    enabled: !!id,
    refetchInterval: (query) => {
      const data = query.state.data;
      return data?.status === 'RUNNING' ? 2000 : false;
    },
  });
}

export function useStartAnalysisMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: startAnalysisApi,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['analysis', data.analysisId] });
    },
  });
}
