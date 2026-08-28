'use client';

import React from 'react';
import { Activity } from 'lucide-react';

interface NavbarProps {
  status: 'idle' | 'loading_scores' | 'scores_ready' | 'analyzing' | 'completed' | 'error';
  statusMessage?: string;
}

export const Navbar: React.FC<NavbarProps> = ({ status }) => {
  const getStatusChip = () => {
    const base: React.CSSProperties = {
      display: 'inline-flex',
      alignItems: 'center',
      gap: 4,
      padding: '3px 8px',
      fontSize: '0.6875rem',
      fontWeight: 700,
      textTransform: 'uppercase',
      letterSpacing: '0.04em',
      borderRadius: 3,
    };
  };

  return (
    <header
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '10px 24px',
        backgroundColor: '#1c4b5a',
        borderBottom: '1px solid #153843',
        color: '#ffffff',
        position: 'sticky',
        top: 0,
        zIndex: 50,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: '1.125rem', fontWeight: 800, color: '#ffffff', letterSpacing: '-0.01em' }}>
              DataMend
            </span>
          </div>
          <p style={{ fontSize: '0.6875rem', color: '#94a3b8', margin: 0, marginTop: 1 }}>
            Time-Series Anomaly Detection Platform
          </p>
        </div>
      </div>
    </header>
  );
};
