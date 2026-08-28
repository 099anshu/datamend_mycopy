'use client';

import React, { useState, useMemo } from 'react';
import { Download, Search, AlertTriangle } from 'lucide-react';
import { AnomalyItem } from '@/types/api';

interface AnomaliesTableProps {
  anomalies: AnomalyItem[];
}

export const AnomaliesTable: React.FC<AnomaliesTableProps> = ({ anomalies }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');
  const [page, setPage] = useState(1);
  const pageSize = 10;

  const filtered = useMemo(() => {
    return anomalies.filter((a) => {
      const col = (a.columnName || a.column || '').toLowerCase();
      const time = (a.timestamp || '').toLowerCase();
      const matchSearch = col.includes(searchTerm.toLowerCase()) || time.includes(searchTerm.toLowerCase());
      const matchSeverity = severityFilter === 'ALL' || a.severity === severityFilter;
      return matchSearch && matchSeverity;
    });
  }, [anomalies, searchTerm, severityFilter]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
  const pageItems = filtered.slice((page - 1) * pageSize, page * pageSize);

  const handleExportJson = () => {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(anomalies, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute('download', `datamend-anomalies-${Date.now()}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  if (anomalies.length === 0) {
    return null;
  }

  return (
    <div className="panel">
      {/* Edge-to-edge Header Bar */}
      <div className="panel-header">
        <div>
          <div className="panel-header-title">
            <span>Detected Anomaly Incidents ({filtered.length})</span>
          </div>
          <div className="panel-header-subtitle">
            Log of sequence timestamps exceeding detection threshold
          </div>
        </div>

        <button
          type="button"
          onClick={handleExportJson}
          className="btn btn-secondary"
          style={{ padding: '4px 10px', fontSize: '0.6875rem' }}
        >
          <Download size={12} /> Export JSON
        </button>
      </div>

      <div className="panel-body" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {/* Filters */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center' }}>
          <div style={{ position: 'relative', flex: 1, minWidth: 200 }}>
            <Search
              size={13}
              style={{ position: 'absolute', left: 9, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }}
            />
            <input
              type="text"
              className="form-input"
              placeholder="Filter by timestamp or channel..."
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                setPage(1);
              }}
              style={{ paddingLeft: 28, fontSize: '0.8125rem' }}
            />
          </div>

          <div style={{ display: 'flex', gap: 4 }}>
            {['ALL', 'HIGH', 'MEDIUM', 'LOW'].map((sev) => {
              const isSelected = severityFilter === sev;
              return (
                <button
                  key={sev}
                  type="button"
                  onClick={() => {
                    setSeverityFilter(sev);
                    setPage(1);
                  }}
                  style={{
                    backgroundColor: isSelected ? '#1c4b5a' : '#ffffff',
                    border: `1px solid ${isSelected ? '#1c4b5a' : 'var(--border)'}`,
                    color: isSelected ? '#ffffff' : 'var(--text-secondary)',
                    borderRadius: 3,
                    padding: '4px 8px',
                    fontSize: '0.6875rem',
                    fontWeight: 700,
                    cursor: 'pointer',
                  }}
                >
                  {sev}
                </button>
              );
            })}
          </div>
        </div>

        {/* Table */}
        <div style={{ overflowX: 'auto', border: '1px solid var(--border)', borderRadius: 4 }}>
          <table className="data-table" aria-label="Detected Anomaly Incidents Table">
            <thead>
              <tr>
                <th scope="col">Timestamp</th>
                <th scope="col">Signal Channel</th>
                <th scope="col">Observed Value</th>
                <th scope="col">Score</th>
                <th scope="col">Severity</th>
              </tr>
            </thead>
            <tbody>
              {pageItems.map((item, idx) => {
                const col = item.columnName || item.column || '—';
                return (
                  <tr key={idx}>
                    <td className="tabular-nums" style={{ color: 'var(--text-secondary)' }}>
                      {item.timestamp}
                    </td>
                    <td style={{ fontWeight: 700, color: '#1c4b5a' }}>
                      {col}
                    </td>
                    <td className="tabular-nums">
                      {typeof item.value === 'number' ? item.value.toFixed(3) : '—'}
                    </td>
                    <td className="tabular-nums" style={{ color: '#d32f2f', fontWeight: 700 }}>
                      {typeof item.score === 'number' ? item.score.toFixed(4) : '—'}
                    </td>
                    <td>
                      <span
                        className={`chip ${
                          item.severity === 'HIGH'
                            ? 'chip-critical'
                            : item.severity === 'MEDIUM'
                            ? 'chip-warning'
                            : 'chip-info'
                        }`}
                      >
                        {item.severity}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: 2 }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Page {page} of {totalPages} ({filtered.length} total entries)
            </span>
            <div style={{ display: 'flex', gap: 4 }}>
              <button
                type="button"
                className="btn btn-secondary"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
                style={{ padding: '3px 8px', fontSize: '0.6875rem' }}
              >
                Previous
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
                style={{ padding: '3px 8px', fontSize: '0.6875rem' }}
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
