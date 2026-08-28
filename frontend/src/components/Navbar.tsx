'use client';

import React from 'react';
import { Activity, Server } from 'lucide-react';

interface NavbarProps {
  status: 'idle' | 'loading_scores' | 'scores_ready' | 'analyzing' | 'completed' | 'error';
  statusMessage: string;
}

export const Navbar: React.FC<NavbarProps> = ({ status }) => {
  const getStatusChip = () => {
    switch (status) {
      case 'loading_scores':
      case 'analyzing':
        return (
          <span className="chip chip-info" style={{ padding: '4px 8px' }}>
            <span className="animate-spin" style={{ display: 'inline-block', marginRight: 4 }}>⟳</span>
            {status === 'loading_scores' ? 'FETCHING' : 'ANALYZING'}
          </span>
        );
      case 'completed':
        return (
          <span className="chip chip-success" style={{ padding: '4px 8px' }}>
            ● COMPLETED
          </span>
        );
      case 'error':
        return (
          <span className="chip chip-critical" style={{ padding: '4px 8px' }}>
            ▲ ERROR
          </span>
        );
      default:
        return (
          <span className="chip chip-neutral" style={{ padding: '4px 8px', color: '#1c4b5a', background: '#e2e8f0' }}>
            ● READY
          </span>
        );
    }
  };

  return (
    <header
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '12px 24px',
        backgroundColor: 'var(--panel-header)',
        borderBottom: '1px solid #153843',
        color: '#ffffff',
        position: 'sticky',
        top: 0,
        zIndex: 100,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: '1.125rem', fontWeight: 800, letterSpacing: '-0.02em', color: '#ffffff' }}>
              DataMend
            </span>
          </div>
          <p style={{ fontSize: '0.6875rem', color: '#94a3b8' }}>
            Time-Series Anomaly Detection Platform
          </p>
        </div>
      </div>
    </header>
  );
};
