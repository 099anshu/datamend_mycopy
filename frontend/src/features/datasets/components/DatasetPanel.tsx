'use client';

import React, { useCallback, useState } from 'react';
import { Database, RotateCcw } from 'lucide-react';
import { Panel } from '@/shared/ui';
import { DATASET_PRESETS } from '@/lib/config';
import { useAnalysisStore } from '@/features/analysis/hooks/useAnalysis';
import { useAnalysisConfig } from '@/features/analysis/hooks/useAnalysisConfig';
import { DatasetUpload } from './DatasetUpload';
import { ColumnMapper } from './ColumnMapper';
import { useDatasetSelection } from '../hooks/useDatasetSelection';
import { getDatasetApi, useUploadedDatasetsQuery } from '../services/datasetApi';
import { UploadedDataset } from '../services/schemas';

export const DatasetPanel: React.FC = () => {
  const {
    datasetSource,
    setDatasetSource,
    uploadedDatasetId,
    uploadedDatasetName,
    uploadedProfile,
    timestampColumn,
    setTimestampColumn,
    applyUploadedDataset,
    clearUploadedDataset,
    selectedColumns,
    setSelectedColumns,
    blockingReason,
  } = useDatasetSelection();

  const datasetName = useAnalysisStore((s) => s.datasetName);
  const setDatasetName = useAnalysisStore((s) => s.setDatasetName);
  const columnsInput = useAnalysisStore((s) => s.columnsInput);
  const setColumnsInput = useAnalysisStore((s) => s.setColumnsInput);
  const { handleApplyPreset } = useAnalysisConfig();

  const uploadedDatasets = useUploadedDatasetsQuery();
  const [loadError, setLoadError] = useState<string | null>(null);

  const handleUploaded = useCallback(
    (dataset: UploadedDataset) => {
      applyUploadedDataset(dataset);
      void uploadedDatasets.refetch();
    },
    [applyUploadedDataset, uploadedDatasets]
  );

  const handleSelectExisting = useCallback(
    async (datasetId: string) => {
      setLoadError(null);
      try {
        applyUploadedDataset(await getDatasetApi(datasetId));
      } catch (err: unknown) {
        setLoadError(err instanceof Error ? err.message : 'Failed to load dataset');
      }
    },
    [applyUploadedDataset]
  );

  return (
    <Panel title="Dataset" icon={<Database size={15} />} style={{ overflow: 'visible' }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        <div
          style={{
            display: 'flex',
            gap: 4,
            padding: 3,
            borderRadius: 6,
            backgroundColor: '#f1f5f9',
          }}
        >
          <button
            type="button"
            className="source-tab"
            data-active={datasetSource === 'upload'}
            onClick={() => setDatasetSource('upload')}
          >
            Upload
          </button>
          <button
            type="button"
            className="source-tab"
            data-active={datasetSource === 'tsdb'}
            onClick={() => setDatasetSource('tsdb')}
          >
            Built-in (TSDB)
          </button>
        </div>

        {datasetSource === 'upload' ? (
          <>
            <DatasetUpload onUploaded={handleUploaded} />

            {uploadedDatasets.data && uploadedDatasets.data.length > 0 && (
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label className="form-label" htmlFor="existing-dataset">
                  Previously uploaded
                </label>
                <select
                  id="existing-dataset"
                  className="form-select"
                  value={uploadedDatasetId ?? ''}
                  onChange={(event) => {
                    if (event.target.value) {
                      void handleSelectExisting(event.target.value);
                    } else {
                      clearUploadedDataset();
                    }
                  }}
                >
                  <option value="">Select a dataset…</option>
                  {uploadedDatasets.data.map((dataset) => (
                    <option key={dataset.datasetId} value={dataset.datasetId}>
                      {dataset.name} · {dataset.rowCount.toLocaleString()} rows
                    </option>
                  ))}
                </select>
              </div>
            )}

            {loadError && (
              <div style={{ fontSize: '0.6875rem', fontWeight: 600, color: '#991b1b' }}>{loadError}</div>
            )}

            {uploadedProfile && (
              <>
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: 8,
                  }}
                >
                  <span className="code-font" style={{ fontSize: '0.75rem', fontWeight: 700 }}>
                    {uploadedDatasetName}
                  </span>
                  <button
                    type="button"
                    onClick={clearUploadedDataset}
                    title="Clear selection"
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 4,
                      background: 'none',
                      border: 'none',
                      padding: 0,
                      fontSize: '0.6875rem',
                      color: '#1a56c4',
                      cursor: 'pointer',
                    }}
                  >
                    <RotateCcw size={11} />
                    Clear
                  </button>
                </div>

                <ColumnMapper
                  profile={uploadedProfile}
                  timestampColumn={timestampColumn}
                  selectedColumns={selectedColumns}
                  onTimestampColumnChange={setTimestampColumn}
                  onSelectedColumnsChange={setSelectedColumns}
                />
              </>
            )}

            {blockingReason && (
              <div style={{ fontSize: '0.6875rem', color: '#5b6472' }}>{blockingReason}</div>
            )}
          </>
        ) : (
          <>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label className="form-label" htmlFor="dataset-input">
                Time-Series Dataset (TSDB)
              </label>
              <input
                id="dataset-input"
                type="text"
                className="form-input"
                value={datasetName}
                onChange={(event) => setDatasetName(event.target.value)}
                placeholder="e.g. ETTh1, ETTm1"
              />
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 4 }}>
                {DATASET_PRESETS.map((preset) => {
                  const isSelected = datasetName === preset.name;
                  return (
                    <button
                      key={preset.name}
                      type="button"
                      onClick={() => handleApplyPreset(preset)}
                      style={{
                        padding: '2px 8px',
                        borderRadius: 3,
                        fontSize: '0.6875rem',
                        fontWeight: 700,
                        border: '1px solid',
                        borderColor: isSelected ? '#1c4b5a' : '#d7dbe0',
                        backgroundColor: isSelected ? '#1c4b5a' : '#ffffff',
                        color: isSelected ? '#ffffff' : '#475569',
                        cursor: 'pointer',
                        fontFamily: 'inherit',
                      }}
                    >
                      {preset.name}
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="form-group" style={{ marginBottom: 0 }}>
              <label className="form-label" htmlFor="columns-input">
                Signal Columns
              </label>
              <textarea
                id="columns-input"
                className="form-input"
                style={{ resize: 'vertical' }}
                rows={2}
                value={columnsInput}
                onChange={(event) => setColumnsInput(event.target.value)}
              />
            </div>
          </>
        )}
      </div>
    </Panel>
  );
};
