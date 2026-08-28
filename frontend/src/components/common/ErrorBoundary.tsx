'use client';

import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallbackTitle?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error in component:', error, errorInfo);
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div
          className="panel"
          style={{
            padding: '24px',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 12,
            backgroundColor: 'var(--status-critical-bg)',
            borderColor: '#fca5a5',
          }}
          role="alert"
        >
          <AlertTriangle size={24} color="var(--status-critical)" />
          <div style={{ textAlign: 'center' }}>
            <h4 style={{ fontSize: '0.875rem', fontWeight: 700, color: '#991b1b' }}>
              {this.props.fallbackTitle || 'Component Failed to Render'}
            </h4>
            <p style={{ fontSize: '0.75rem', color: '#b91c1c', marginTop: 4 }}>
              {this.state.error?.message || 'An unexpected rendering error occurred.'}
            </p>
          </div>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={this.handleReset}
            style={{ padding: '4px 10px', fontSize: '0.75rem' }}
          >
            <RefreshCw size={12} /> Retry Rendering
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
