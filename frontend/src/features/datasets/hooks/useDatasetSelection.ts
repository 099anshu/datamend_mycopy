'use client';

import { useCallback, useMemo } from 'react';
import { useAnalysisStore } from '@/features/analysis/hooks/useAnalysis';
import { UploadedDataset } from '../services/schemas';

export function useDatasetSelection() {
  const datasetSource = useAnalysisStore((s) => s.datasetSource);
  const setDatasetSource = useAnalysisStore((s) => s.setDatasetSource);
  const uploadedDatasetId = useAnalysisStore((s) => s.uploadedDatasetId);
  const uploadedDatasetName = useAnalysisStore((s) => s.uploadedDatasetName);
  const uploadedProfile = useAnalysisStore((s) => s.uploadedProfile);
  const timestampColumn = useAnalysisStore((s) => s.timestampColumn);
  const setTimestampColumn = useAnalysisStore((s) => s.setTimestampColumn);
  const selectUploadedDataset = useAnalysisStore((s) => s.selectUploadedDataset);
  const columnsInput = useAnalysisStore((s) => s.columnsInput);
  const setColumnsInput = useAnalysisStore((s) => s.setColumnsInput);

  const selectedColumns = useMemo(
    () =>
      columnsInput
        .split(',')
        .map((column) => column.trim())
        .filter(Boolean),
    [columnsInput]
  );

  const setSelectedColumns = useCallback(
    (columns: string[]) => setColumnsInput(columns.join(',')),
    [setColumnsInput]
  );

  const applyUploadedDataset = useCallback(
    (dataset: UploadedDataset) =>
      selectUploadedDataset({
        datasetId: dataset.datasetId,
        name: dataset.name,
        profile: dataset.profile,
      }),
    [selectUploadedDataset]
  );

  const blockingReason = useMemo(() => {
    if (datasetSource !== 'upload') {
      return null;
    }
    if (!uploadedDatasetId) {
      return 'Upload or pick a dataset to analyse.';
    }
    if (!timestampColumn) {
      return 'Select the timestamp column for this dataset.';
    }
    if (selectedColumns.length === 0) {
      return 'Select at least one signal column.';
    }
    return null;
  }, [datasetSource, uploadedDatasetId, timestampColumn, selectedColumns.length]);

  return {
    datasetSource,
    setDatasetSource,
    uploadedDatasetId,
    uploadedDatasetName,
    uploadedProfile,
    timestampColumn,
    setTimestampColumn,
    applyUploadedDataset,
    clearUploadedDataset: useCallback(() => selectUploadedDataset(null), [selectUploadedDataset]),
    selectedColumns,
    setSelectedColumns,
    blockingReason,
    isReady: blockingReason === null,
  };
}
