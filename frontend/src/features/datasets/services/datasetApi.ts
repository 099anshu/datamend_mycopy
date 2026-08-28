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

export async function calculateRollingApi(
  source: string,
  datasetName: string,
  columns: string[],
  window: number = 24,
  timestampColumn?: string
): Promise<{ status: string; window: number; data: any[]; columns: string[] }> {
  const form = new FormData();
  form.append('source', source);
  form.append('datasetName', datasetName);
  columns.forEach(col => form.append('columns', col));
  form.append('window', window.toString());
  if (timestampColumn) {
    form.append('timestampColumn', timestampColumn);
  }

  const res = await fetch(`${API_BASE}/api/v1/analysis/rolling`, { method: 'POST', body: form });
  if (!res.ok) {
    throw await parseError(res, 'Failed to calculate rolling statistics');
  }
  return res.json();
}

export async function calculateDifferencesApi(
  source: string,
  datasetName: string,
  columns: string[],
  periods: number = 1,
  timestampColumn?: string
): Promise<{ status: string; periods: number; data: any[]; columns: string[] }> {
  const form = new FormData();
  form.append('source', source);
  form.append('datasetName', datasetName);
  columns.forEach(col => form.append('columns', col));
  form.append('periods', periods.toString());
  if (timestampColumn) {
    form.append('timestampColumn', timestampColumn);
  }

  const res = await fetch(`${API_BASE}/api/v1/analysis/differences`, { method: 'POST', body: form });
  if (!res.ok) {
    throw await parseError(res, 'Failed to calculate differences');
  }
  return res.json();
}

export async function scaleDataApi(
  source: string,
  datasetName: string,
  columns: string[],
  method: string = 'standard',
  timestampColumn?: string
): Promise<{ status: string; method: string; data: any[]; columns: string[] }> {
  const form = new FormData();
  form.append('source', source);
  form.append('datasetName', datasetName);
  columns.forEach(col => form.append('columns', col));
  form.append('method', method);
  if (timestampColumn) {
    form.append('timestampColumn', timestampColumn);
  }

  const res = await fetch(`${API_BASE}/api/v1/analysis/scale`, { method: 'POST', body: form });
  if (!res.ok) {
    throw await parseError(res, 'Failed to scale data');
  }
  return res.json();
}
