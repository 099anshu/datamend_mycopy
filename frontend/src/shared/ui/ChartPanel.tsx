'use client';

import React from 'react';
import { AlertTriangle, RotateCcw, Layers } from 'lucide-react';
import { Panel, PanelProps } from './Panel';

export interface ChartPanelProps extends Omit<PanelProps, 'children'> {
  height?: number | string;
  status?: 'loading' | 'empty' | 'error' | 'ready';
  errorMessage?: string;
  emptyMessage?: string;
  children: React.ReactNode;
}

export const ChartPanel: React.FC<ChartPanelProps> = ({
  height = 360,
  status = 'ready',
  errorMessage,
  emptyMessage = 'No time-series data loaded. Click "Load Series & Scores" to fetch signals.',
  children,
  ...panelProps
}) => {
  const containerStyle: React.CSSProperties = {
    height: typeof height === 'number' ? `${height}px` : height,
    width: '100%',
  };

  return (
    <Panel {...panelProps}>
      {status === 'loading' && (
        <div
          style={{
            ...containerStyle,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 8,
            color: '#64748b',
          }}
        >
          <RotateCcw size={22} color="#1a56c4" style={{ animation: 'spin 1s linear infinite' }} />
          <p style={{ fontSize: '0.75rem', margin: 0 }}>Loading chart data...</p>
        </div>
      )}

      {status === 'empty' && (
        <div
          style={{
            ...containerStyle,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 8,
            color: '#94a3b8',
          }}
        >
          <Layers size={28} color="#cbd5e1" />
          <p style={{ fontSize: '0.75rem', margin: 0, textAlign: 'center', maxWidth: 320 }}>
            {emptyMessage}
          </p>
        </div>
      )}

      {status === 'error' && (
        <div
          style={{
            ...containerStyle,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 8,
            backgroundColor: '#fef2f2',
            color: '#991b1b',
            borderRadius: 4,
            padding: '0 24px',
          }}
        >
          <AlertTriangle size={24} color="#ef4444" />
          <p style={{ fontSize: '0.75rem', fontWeight: 600, margin: 0 }}>
            {errorMessage || 'Failed to render chart'}
          </p>
        </div>
      )}

      {status === 'ready' && <div style={{ ...containerStyle, padding: 12 }}>{children}</div>}
    </Panel>
  );
};