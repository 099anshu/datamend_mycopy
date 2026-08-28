'use client';

import React, { useCallback, useRef, useState } from 'react';
import { UploadCloud, Loader2 } from 'lucide-react';
import { uploadDatasetApi } from '../services/datasetApi';
import { UploadedDataset } from '../services/schemas';

interface DatasetUploadProps {
  onUploaded: (dataset: UploadedDataset) => void;
  disabled?: boolean;
}

const ACCEPTED = '.csv,.tsv,.txt';

export const DatasetUpload: React.FC<DatasetUploadProps> = ({ onUploaded, disabled }) => {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const upload = useCallback(
    async (file: File) => {
      setIsUploading(true);
      setError(null);
      try {
        onUploaded(await uploadDatasetApi(file));
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : 'Upload failed');
      } finally {
        setIsUploading(false);
      }
    },
    [onUploaded]
  );

  const handleDrop = useCallback(
    (event: React.DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      setIsDragging(false);
      const file = event.dataTransfer.files?.[0];
      if (file && !disabled) {
        void upload(file);
      }
    },
    [disabled, upload]
  );

  const busy = isUploading || disabled;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <div
        onDragOver={(event) => {
          event.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onClick={() => !busy && inputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(event) => {
          if (!busy && (event.key === 'Enter' || event.key === ' ')) {
            inputRef.current?.click();
          }
        }}
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 6,
          padding: '18px 12px',
          borderRadius: 6,
          border: `1px dashed ${isDragging ? '#1a56c4' : '#d7dbe0'}`,
          backgroundColor: isDragging ? '#eff6ff' : '#f8fafc',
          cursor: busy ? 'progress' : 'pointer',
          textAlign: 'center',
          opacity: disabled ? 0.6 : 1,
        }}
      >
        {isUploading ? (
          <Loader2 size={18} color="#1a56c4" className="spin" />
        ) : (
          <UploadCloud size={18} color="#1a56c4" />
        )}
        <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#1e293b' }}>
          {isUploading ? 'Uploading and profiling…' : 'Drop a CSV here or click to browse'}
        </div>
        <div style={{ fontSize: '0.6875rem', color: '#5b6472' }}>
          CSV or TSV with a timestamp column and one or more numeric signals
        </div>
      </div>

      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED}
        style={{ display: 'none' }}
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) {
            void upload(file);
          }
          event.target.value = '';
        }}
      />

      {error && (
        <div style={{ fontSize: '0.6875rem', fontWeight: 600, color: '#991b1b' }}>{error}</div>
      )}
    </div>
  );
};
