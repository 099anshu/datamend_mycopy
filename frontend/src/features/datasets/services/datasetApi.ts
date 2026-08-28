import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';
import {
  UploadedDataset,
  UploadedDatasetSchema,
  UploadedDatasetSummary,
  UploadedDatasetSummarySchema,
} from './schemas';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';

async function parseError(res: Response, fallback: string): Promise<Error> {
  const body = await res.json().catch(() => ({}));
  // The backend forwards ml-service failures as a raw JSON string under `error`.
  const raw = body.detail || body.error || `HTTP ${res.status}: ${fallback}`;
  if (typeof raw === 'string' && raw.trim().startsWith('{')) {
    try {
      const nested = JSON.parse(raw);
      return new Error(nested.detail || nested.error || raw);
    } catch {
      return new Error(raw);
    }
  }
  return new Error(String(raw));
}

export async function uploadDatasetApi(
  file: File,
  timestampColumn?: string
): Promise<UploadedDataset> {
  const form = new FormData();
  form.append('file', file);
  if (timestampColumn) {
    form.append('timestampColumn', timestampColumn);
  }

  const res = await fetch(`${API_BASE}/api/v1/datasets`, { method: 'POST', body: form });
  if (!res.ok) {
    throw await parseError(res, 'Failed to upload dataset');
  }
  return UploadedDatasetSchema.parse(await res.json());
}

export async function listDatasetsApi(): Promise<UploadedDatasetSummary[]> {
  const res = await fetch(`${API_BASE}/api/v1/datasets`, { headers: { Accept: 'application/json' } });
  if (!res.ok) {
    throw await parseError(res, 'Failed to list datasets');
  }
  return UploadedDatasetSummarySchema.array().parse(await res.json());
}

export async function getDatasetApi(datasetId: string): Promise<UploadedDataset> {
  const res = await fetch(`${API_BASE}/api/v1/datasets/${encodeURIComponent(datasetId)}`, {
    headers: { Accept: 'application/json' },
  });
  if (!res.ok) {
    throw await parseError(res, 'Failed to fetch dataset');
  }
  return UploadedDatasetSchema.parse(await res.json());
}

export async function listTsdbDatasetsApi(): Promise<string[]> {
  const res = await fetch(`${API_BASE}/api/v1/datasets/sources/tsdb`, {
    headers: { Accept: 'application/json' },
  });
  if (!res.ok) {
    throw await parseError(res, 'Failed to list TSDB datasets');
  }
  return z.array(z.string()).parse(await res.json());
}

export function useUploadedDatasetsQuery() {
  return useQuery({
    queryKey: ['datasets'],
    queryFn: listDatasetsApi,
    staleTime: 15000,
  });
}
