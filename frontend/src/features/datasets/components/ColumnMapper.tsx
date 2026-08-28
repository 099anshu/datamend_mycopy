'use client';

import React, { useMemo, useState } from 'react';
import { ChevronDown, ChevronRight, AlertTriangle } from 'lucide-react';
import { DatasetProfile } from '../services/schemas';

interface ColumnMapperProps {
  profile: DatasetProfile;
  timestampColumn: string | null;
  selectedColumns: string[];
  onTimestampColumnChange: (column: string | null) => void;
  onSelectedColumnsChange: (columns: string[]) => void;
}

const formatNumber = (value: number | null | undefined): string =>
  value === null || value === undefined ? '—' : Number(value).toLocaleString(undefined, { maximumFractionDigits: 3 });

export const ColumnMapper: React.FC<ColumnMapperProps> = ({
  profile,
  timestampColumn,
  selectedColumns,
  onTimestampColumnChange,
  onSelectedColumnsChange,
}) => {
  const [showPreview, setShowPreview] = useState(false);

  const timestampCandidates = useMemo(
    () => profile.columns.filter((column) => column.kind !== 'numeric' || column.name === timestampColumn),
    [profile.columns, timestampColumn]
  );

  const signalCandidates = useMemo(
    () => profile.columns.filter((column) => column.kind === 'numeric' && column.name !== timestampColumn),
    [profile.columns, timestampColumn]
  );

  const previewColumns = useMemo(
    () => profile.columns.map((column) => column.name).slice(0, 8),
    [profile.columns]
  );

  const toggleColumn = (name: string) => {
    onSelectedColumnsChange(
      selectedColumns.includes(name)
        ? selectedColumns.filter((column) => column !== name)
        : [...selectedColumns, name]
    );
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ display: 'flex', gap: 12, fontSize: '0.6875rem', color: '#5b6472' }}>
        <span>
          <strong style={{ color: '#0f172a' }}>{profile.rowCount.toLocaleString()}</strong> rows
        </span>
        <span>
          <strong style={{ color: '#0f172a' }}>{profile.columnCount}</strong> columns
        </span>
        <span>
          <strong style={{ color: '#0f172a' }}>{signalCandidates.length}</strong> numeric signals
        </span>
      </div>

      <div className="form-group" style={{ marginBottom: 0 }}>
        <label className="form-label" htmlFor="timestamp-column">
          Timestamp column
        </label>
        <select
          id="timestamp-column"
          className="form-select"
          value={timestampColumn ?? ''}
          onChange={(event) => onTimestampColumnChange(event.target.value || null)}
        >
          <option value="">Select a timestamp column…</option>
          {timestampCandidates.map((column) => (
            <option key={column.name} value={column.name}>
              {column.name} ({column.dtype})
            </option>
          ))}
        </select>
        {!timestampColumn && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 4,
              fontSize: '0.6875rem',
              fontWeight: 600,
              color: '#92400e',
            }}
          >
            <AlertTriangle size={12} />
            No timestamp detected — pick the column that holds the time index.
          </div>
        )}
      </div>

      <div className="form-group" style={{ marginBottom: 0 }}>
        <label className="form-label">Signal columns ({selectedColumns.length} selected)</label>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          {signalCandidates.map((column) => {
            const selected = selectedColumns.includes(column.name);
            return (
              <button
                key={column.name}
                type="button"
                className="column-toggle"
                data-selected={selected}
                onClick={() => toggleColumn(column.name)}
                title={`min ${formatNumber(column.min)} · max ${formatNumber(column.max)} · nulls ${(
                  column.nullRate * 100
                ).toFixed(1)}%`}
              >
                <input type="checkbox" checked={selected} readOnly tabIndex={-1} />
                <span className="code-font">{column.name}</span>
                {column.nullRate > 0 && (
                  <span style={{ fontSize: '0.625rem', color: '#92400e' }}>
                    {(column.nullRate * 100).toFixed(0)}% null
                  </span>
                )}
              </button>
            );
          })}
        </div>
        {signalCandidates.length > 0 && (
          <div style={{ display: 'flex', gap: 8, fontSize: '0.6875rem' }}>
            <button
              type="button"
              onClick={() => onSelectedColumnsChange(signalCandidates.map((column) => column.name))}
              style={{ background: 'none', border: 'none', color: '#1a56c4', cursor: 'pointer', padding: 0 }}
            >
              Select all
            </button>
            <button
              type="button"
              onClick={() => onSelectedColumnsChange([])}
              style={{ background: 'none', border: 'none', color: '#1a56c4', cursor: 'pointer', padding: 0 }}
            >
              Clear
            </button>
          </div>
        )}
      </div>

      <div>
        <button
          type="button"
          onClick={() => setShowPreview((value) => !value)}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 4,
            background: 'none',
            border: 'none',
            padding: 0,
            fontSize: '0.6875rem',
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            color: '#475569',
            cursor: 'pointer',
          }}
        >
          {showPreview ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
          Preview ({profile.preview.length} rows)
        </button>

        {showPreview && (
          <div style={{ overflowX: 'auto', marginTop: 8, border: '1px solid #d7dbe0', borderRadius: 4 }}>
            <table className="data-table">
              <thead>
                <tr>
                  {previewColumns.map((name) => (
                    <th key={name}>{name}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {profile.preview.slice(0, 10).map((row, index) => (
                  <tr key={index}>
                    {previewColumns.map((name) => (
                      <td key={name} className="code-font">
                        {row[name] === null || row[name] === undefined ? '—' : String(row[name])}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
