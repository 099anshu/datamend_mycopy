'use client';

import React from 'react';
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
} from 'recharts';
import { PieChart as PieIcon, BarChart2 } from 'lucide-react';
import { AnomalyItem } from '@/types/api';

interface SeverityDistributionChartProps {
  anomalies: AnomalyItem[];
  columns: string[];
}

export const SeverityDistributionChart: React.FC<SeverityDistributionChartProps> = ({
  anomalies,
}) => {
  if (anomalies.length === 0) return null;

  const severityCounts = {
    HIGH: anomalies.filter((a) => a.severity === 'HIGH').length,
    MEDIUM: anomalies.filter((a) => a.severity === 'MEDIUM').length,
    LOW: anomalies.filter((a) => a.severity === 'LOW').length,
  };

  const pieData = [
    { name: 'HIGH', value: severityCounts.HIGH, color: '#d32f2f' },
    { name: 'MEDIUM', value: severityCounts.MEDIUM, color: '#e69100' },
    { name: 'LOW', value: severityCounts.LOW, color: '#1a56c4' },
  ].filter((d) => d.value > 0);

  // Column distribution
  const colCounts: Record<string, number> = {};
  anomalies.forEach((a) => {
    const col = a.columnName || a.column || 'unknown';
    colCounts[col] = (colCounts[col] || 0) + 1;
  });

  const barData = Object.keys(colCounts).map((col) => ({
    column: col,
    count: colCounts[col],
  }));

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 12 }}>
      {/* Severity Breakdown */}
      <div className="panel">
        <div className="panel-header">
          <div className="panel-header-title">
            <span>Severity Distribution</span>
          </div>
        </div>

        <div className="panel-body">
          <div style={{ width: '100%', height: 170 }}>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={pieData}
                  innerRadius={44}
                  outerRadius={68}
                  paddingAngle={3}
                  dataKey="value"
                >
                  {pieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  content={({ active, payload }) => {
                    if (!active || !payload || !payload.length) return null;
                    const item = payload[0];
                    return (
                      <div
                        style={{
                          backgroundColor: '#ffffff',
                          border: '1px solid var(--border)',
                          padding: '6px 10px',
                          borderRadius: 4,
                          boxShadow: '0 2px 8px rgba(0, 0, 0, 0.08)',
                          fontSize: '0.75rem',
                        }}
                      >
                        <span style={{ color: item.payload.color, fontWeight: 700 }}>{item.name}: </span>
                        <span className="tabular-nums" style={{ fontWeight: 600 }}>{item.value} anomalies</span>
                      </div>
                    );
                  }}
                />
                <Legend verticalAlign="bottom" height={30} iconType="circle" wrapperStyle={{ fontSize: '0.6875rem' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Sensor/Column Breakdown */}
      <div className="panel">
        <div className="panel-header">
          <div className="panel-header-title">
            <BarChart2 size={15} />
            <span>Anomalies by Channel</span>
          </div>
        </div>

        <div className="panel-body">
          <div style={{ width: '100%', height: 170 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={barData} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="column" stroke="#64748b" fontSize={10} tickLine={false} />
                <YAxis stroke="#64748b" fontSize={10} tickLine={false} allowDecimals={false} />
                <Tooltip
                  content={({ active, payload }) => {
                    if (!active || !payload || !payload.length) return null;
                    return (
                      <div
                        style={{
                          backgroundColor: '#ffffff',
                          border: '1px solid var(--border)',
                          padding: '6px 10px',
                          borderRadius: 4,
                          boxShadow: '0 2px 8px rgba(0, 0, 0, 0.08)',
                          fontSize: '0.75rem',
                        }}
                      >
                        <strong>{payload[0].payload.column}: </strong>
                        <span className="tabular-nums">{payload[0].value} anomalies</span>
                      </div>
                    );
                  }}
                />
                <Bar dataKey="count" fill="#1c4b5a" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
};
