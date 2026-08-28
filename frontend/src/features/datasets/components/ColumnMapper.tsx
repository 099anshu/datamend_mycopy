'use client';

import React, { useEffect, useMemo, useRef, useState } from 'react';
import { ChevronDown, ChevronRight, Check, AlertTriangle, Pencil, X } from 'lucide-react';
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
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  // Whether the user is overriding the auto-detected timestamp column
  const [overrideTimestamp, setOverrideTimestamp] = useState(false);
  const [overrideValue, setOverrideValue] = useState<string>('');

  // Auto-apply detected timestamp column — no manual picker needed for TS files
  useEffect(() => {
    if (profile.timestampColumn && !timestampColumn) {
      onTimestampColumnChange(profile.timestampColumn);
    }
  }, [profile.timestampColumn, timestampColumn, onTimestampColumnChange]);

  const timestampCandidates = useMemo(
    () => profile.columns.filter((col) => col.kind !== 'numeric' || col.name === timestampColumn),
    [profile.columns, timestampColumn]
  );

  const signalCandidates = useMemo(
    () => profile.columns.filter((col) => col.kind === 'numeric' && col.name !== timestampColumn),
    [profile.columns, timestampColumn]
  );

  const previewColumns = useMemo(
    () => profile.columns.map((col) => col.name).slice(0, 8),
    [profile.columns]
  );

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    };
    if (dropdownOpen) document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [dropdownOpen]);

  const toggleColumn = (name: string) => {
    onSelectedColumnsChange(
      selectedColumns.includes(name)
        ? selectedColumns.filter((c) => c !== name)
        : [...selectedColumns, name]
    );
  };

  const selectAll = () => onSelectedColumnsChange(signalCandidates.map((c) => c.name));
  const clearAll = () => onSelectedColumnsChange([]);

  const allSelected = signalCandidates.length > 0 && signalCandidates.every((c) => selectedColumns.includes(c.name));
  const noneSelected = selectedColumns.length === 0;

  const needsTimestampPicker = !profile.timestampColumn;

  // All columns available for override selection (any kind)
  const allColumnCandidates = profile.columns;

  // Is the overridden column numeric (bad choice)
  const overrideIsNumeric = overrideValue
    ? profile.columns.find((c) => c.name === overrideValue)?.kind === 'numeric'
    : false;

  const handleConfirmOverride = () => {
    if (overrideValue) {
      onTimestampColumnChange(overrideValue);
    }
    setOverrideTimestamp(false);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {/* Dataset Stats */}
      <div style={{ display: 'flex', gap: 10, fontSize: '0.6875rem', color: '#5b6472' }}>
        <span><strong style={{ color: '#0f172a' }}>{profile.rowCount.toLocaleString()}</strong> rows</span>
        <span><strong style={{ color: '#0f172a' }}>{profile.columnCount}</strong> cols</span>
        <span><strong style={{ color: '#0f172a' }}>{signalCandidates.length}</strong> signals</span>
      </div>

      {/* Timestamp column */}
      {needsTimestampPicker ? (
        <div className="form-group" style={{ marginBottom: 0 }}>
          <label className="form-label" htmlFor="timestamp-column">
            Timestamp column
          </label>
          <select
            id="timestamp-column"
            className="form-select"
            value={timestampColumn ?? ''}
            onChange={(e) => onTimestampColumnChange(e.target.value || null)}
          >
            <option value="">Select timestamp column…</option>
            {timestampCandidates.map((col) => (
              <option key={col.name} value={col.name}>
                {col.name} ({col.dtype})
              </option>
            ))}
          </select>
          {!timestampColumn && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: '0.6875rem', fontWeight: 600, color: '#92400e' }}>
              <AlertTriangle size={11} />
              Pick the column that holds the time index.
            </div>
          )}
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span className="form-label">Timestamp column</span>
            {!overrideTimestamp && (
              <button
                type="button"
                onClick={() => { setOverrideTimestamp(true); setOverrideValue(profile.timestampColumn !== 'auto_generated' ? (profile.timestampColumn ?? '') : ''); }}
                style={{
                  display: 'flex', alignItems: 'center', gap: 3,
                  background: 'none', border: 'none', padding: 0,
                  fontSize: '0.6875rem', color: '#1a56c4', cursor: 'pointer',
                  fontFamily: 'inherit', fontWeight: 600,
                }}
              >
                <Pencil size={10} /> Change
              </button>
            )}
          </div>

          {overrideTimestamp ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              <select
                className="form-select"
                value={overrideValue}
                onChange={(e) => setOverrideValue(e.target.value)}
              >
                <option value="">Select column…</option>
                {allColumnCandidates.map((col) => (
                  <option key={col.name} value={col.name}>
                    {col.name} ({col.dtype})
                  </option>
                ))}
              </select>
              {overrideIsNumeric && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: '0.6875rem', color: '#92400e', fontWeight: 600 }}>
                  <AlertTriangle size={11} />
                  This column is numeric — it may not be a valid timestamp.
                </div>
              )}
              <div style={{ display: 'flex', gap: 6 }}>
                <button
                  type="button"
                  onClick={handleConfirmOverride}
                  disabled={!overrideValue}
                  style={{
                    flex: 1, padding: '4px 0', fontSize: '0.6875rem', fontWeight: 700,
                    backgroundColor: '#1a56c4', color: '#fff', border: 'none',
                    borderRadius: 4, cursor: overrideValue ? 'pointer' : 'not-allowed',
                    opacity: overrideValue ? 1 : 0.5, fontFamily: 'inherit',
                  }}
                >
                  Confirm
                </button>
                <button
                  type="button"
                  onClick={() => setOverrideTimestamp(false)}
                  style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    padding: '4px 8px', fontSize: '0.6875rem', fontWeight: 700,
                    backgroundColor: '#fff', color: '#5b6472',
                    border: '1px solid #d7dbe0', borderRadius: 4, cursor: 'pointer',
                    fontFamily: 'inherit',
                  }}
                >
                  <X size={12} />
                </button>
              </div>
            </div>
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              {profile.timestampColumn !== 'auto_generated' && (
                <span style={{ fontFamily: 'monospace', fontSize: '0.75rem', color: '#0f172a' }}>
                  {timestampColumn ?? profile.timestampColumn}
                </span>
              )}
              {/* auto-detected badge */}
              <span
                style={{
                  display: 'inline-flex', alignItems: 'center',
                  padding: '1px 7px', borderRadius: 10,
                  fontSize: '0.625rem', fontWeight: 700, letterSpacing: '0.03em',
                  color: '#1a56c4',
                  border: '1px solid #1a56c4',
                  backgroundColor: '#eff6ff',
                }}
              >
                auto-detected
              </span>
            </div>
          )}
        </div>
      )}

      {/* Signal Columns — compact checkbox dropdown */}
      <div className="form-group" style={{ marginBottom: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
          <label className="form-label" style={{ margin: 0 }}>
            Signal columns ({selectedColumns.length}/{signalCandidates.length})
          </label>
          {signalCandidates.length > 0 && (
            <div style={{ display: 'flex', gap: 6, fontSize: '0.6875rem' }}>
              <button
                type="button"
                onClick={selectAll}
                style={{ background: 'none', border: 'none', color: '#1a56c4', cursor: 'pointer', padding: 0, fontFamily: 'inherit', fontSize: '0.6875rem' }}
              >
                All
              </button>
              <span style={{ color: '#d7dbe0' }}>|</span>
              <button
                type="button"
                onClick={clearAll}
                style={{ background: 'none', border: 'none', color: '#1a56c4', cursor: 'pointer', padding: 0, fontFamily: 'inherit', fontSize: '0.6875rem' }}
              >
                Clear
              </button>
            </div>
          )}
        </div>

        {/* Dropdown trigger */}
        <div ref={dropdownRef} style={{ position: 'relative' }}>
          <button
            type="button"
            onClick={() => setDropdownOpen((o) => !o)}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              width: '100%',
              padding: '6px 10px',
              fontSize: '0.75rem',
              fontFamily: 'inherit',
              color: noneSelected ? '#94a3b8' : '#0f172a',
              backgroundColor: '#ffffff',
              border: '1px solid #d7dbe0',
              borderRadius: 4,
              cursor: 'pointer',
              boxSizing: 'border-box',
              transition: 'border-color 0.15s',
            }}
          >
            <span>
              {noneSelected
                ? 'Select signal columns…'
                : allSelected
                ? `All ${signalCandidates.length} columns`
                : `${selectedColumns.length} of ${signalCandidates.length} selected`}
            </span>
            <ChevronDown
              size={13}
              color="#5b6472"
              style={{ transform: dropdownOpen ? 'rotate(180deg)' : 'none', transition: 'transform 0.15s', flexShrink: 0 }}
            />
          </button>

          {/* Dropdown panel */}
          {dropdownOpen && (
            <div
              style={{
                position: 'absolute',
                top: 'calc(100% + 4px)',
                left: 0,
                right: 0,
                backgroundColor: '#ffffff',
                border: '1px solid #d7dbe0',
                borderRadius: 4,
                boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
                zIndex: 100,
                maxHeight: 200,
                overflowY: 'auto',
              }}
            >
              {/* Select All row */}
              <div
                onClick={() => (allSelected ? clearAll() : selectAll())}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '6px 10px',
                  fontSize: '0.6875rem',
                  fontWeight: 700,
                  color: '#475569',
                  cursor: 'pointer',
                  borderBottom: '1px solid #f1f5f9',
                  backgroundColor: '#f8fafc',
                  userSelect: 'none',
                }}
              >
                <div
                  style={{
                    width: 14,
                    height: 14,
                    borderRadius: 3,
                    border: '1px solid #94a3b8',
                    backgroundColor: allSelected ? '#1a56c4' : '#ffffff',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                  }}
                >
                  {allSelected && <Check size={10} color="#ffffff" strokeWidth={3} />}
                  {!allSelected && !noneSelected && (
                    <div style={{ width: 8, height: 2, backgroundColor: '#1a56c4' }} />
                  )}
                </div>
                Select all ({signalCandidates.length})
              </div>

              {/* Column rows */}
              {signalCandidates.map((col) => {
                const checked = selectedColumns.includes(col.name);
                return (
                  <div
                    key={col.name}
                    onClick={() => toggleColumn(col.name)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                      padding: '5px 10px',
                      fontSize: '0.75rem',
                      cursor: 'pointer',
                      backgroundColor: checked ? '#eff6ff' : '#ffffff',
                      userSelect: 'none',
                    }}
                    onMouseEnter={(e) => {
                      if (!checked) (e.currentTarget as HTMLDivElement).style.backgroundColor = '#f8fafc';
                    }}
                    onMouseLeave={(e) => {
                      (e.currentTarget as HTMLDivElement).style.backgroundColor = checked ? '#eff6ff' : '#ffffff';
                    }}
                  >
                    <div
                      style={{
                        width: 14,
                        height: 14,
                        borderRadius: 3,
                        border: `1px solid ${checked ? '#1a56c4' : '#94a3b8'}`,
                        backgroundColor: checked ? '#1a56c4' : '#ffffff',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        flexShrink: 0,
                        transition: 'all 0.1s',
                      }}
                    >
                      {checked && <Check size={10} color="#ffffff" strokeWidth={3} />}
                    </div>
                    <span style={{ fontFamily: 'monospace', color: '#0f172a', flex: 1 }}>{col.name}</span>
                    {col.nullRate > 0 && (
                      <span style={{ fontSize: '0.625rem', color: '#92400e', flexShrink: 0 }}>
                        {(col.nullRate * 100).toFixed(0)}% null
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Data preview toggle */}
      <div>
        <button
          type="button"
          onClick={() => setShowPreview((v) => !v)}
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
            fontFamily: 'inherit',
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
                {profile.preview.slice(0, 10).map((row, i) => (
                  <tr key={i}>
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
