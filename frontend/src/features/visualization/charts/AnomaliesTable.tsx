'use client';

import React, { useState, useMemo } from 'react';
import { Download, Search, AlertTriangle } from 'lucide-react';
import { AnomalyItem } from '@/types/api';
import { Panel, Button, Chip } from '@/shared/ui';

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

  if (anomalies.length === 0) return null;

  return (
    <Panel
      title={`Detected Anomaly Incidents (${filtered.length})`}
      subtitle="Log of sequence timestamps exceeding detection threshold"
      icon={<AlertTriangle size={16} />}
      headerActions={
        <Button variant="secondary" size="sm" onClick={handleExportJson} icon={<Download size={12} />}>
          Export JSON
        </Button>
      }
    >
      <div className="flex flex-col gap-3">
        {/* Filters */}
        <div className="flex flex-wrap gap-2 items-center justify-between">
          <div className="relative flex-1 min-w-[200px]">
            <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              className="form-input pl-7 text-xs"
              placeholder="Filter by timestamp or channel..."
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                setPage(1);
              }}
            />
          </div>

          <div className="flex gap-1">
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
                  className={`px-2 py-1 rounded text-[11px] font-bold border transition-colors ${
                    isSelected
                      ? 'bg-panel-header text-white border-panel-header'
                      : 'bg-white text-slate-600 border-border hover:bg-slate-50'
                  }`}
                >
                  {sev}
                </button>
              );
            })}
          </div>
        </div>

        {/* Table */}
        <div className="overflow-x-auto border border-border rounded">
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
                    <td className="tabular-nums text-slate-600">{item.timestamp}</td>
                    <td className="font-bold text-panel-header">{col}</td>
                    <td className="tabular-nums">
                      {typeof item.value === 'number' ? item.value.toFixed(3) : '—'}
                    </td>
                    <td className="tabular-nums font-bold text-status-critical">
                      {typeof item.score === 'number' ? item.score.toFixed(4) : '—'}
                    </td>
                    <td>
                      <Chip variant={item.severity}>{item.severity}</Chip>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between pt-1">
            <span className="text-xs text-slate-500">
              Page {page} of {totalPages} ({filtered.length} total entries)
            </span>
            <div className="flex gap-1">
              <Button
                variant="secondary"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
              >
                Previous
              </Button>
              <Button
                variant="secondary"
                size="sm"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </Button>
            </div>
          </div>
        )}
      </div>
    </Panel>
  );
};
