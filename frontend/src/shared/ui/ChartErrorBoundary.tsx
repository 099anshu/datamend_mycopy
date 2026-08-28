'use client';

import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RotateCcw } from 'lucide-react';

interface ChartErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
  chartName?: string;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  onRetry?: () => void;
}

interface ChartErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class ChartErrorBoundary extends Component<ChartErrorBoundaryProps, ChartErrorBoundaryState> {
  constructor(props: ChartErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ChartErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error(`[ChartErrorBoundary${this.props.chartName ? ` - ${this.props.chartName}` : ''}]`, error, errorInfo);
    this.props.onError?.(error, errorInfo);
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null });
    this.props.onRetry?.();
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="panel" style={{ height: 360 }}>
          <div className="panel-header" style={{ backgroundColor: '#fee2e2', borderBottom: '1px solid #fecaca' }}>
            <div className="panel-header-title" style={{ color: '#991b1b' }}>
              <AlertTriangle size={16} style={{ marginRight: 8 }} />
              <span>{this.props.chartName || 'Chart'} failed to render</span>
            </div>
          </div>
          <div className="panel-body flex flex-col items-center justify-center h-[calc(100%-48px)] gap-3 text-red-900 text-center px-6">
            <AlertTriangle size={32} className="text-red-300" />
            <p className="text-xs font-semibold">
              {this.state.error?.message || 'An unexpected error occurred'}
            </p>
            <details className="text-[10px] text-red-400 text-left max-w-sm w-full">
              <summary className="cursor-pointer mb-1">Error details</summary>
              <pre className="bg-red-50 p-2 rounded overflow-auto whitespace-pre-wrap break-all">
                {this.state.error?.stack}
              </pre>
            </details>
            <button
              type="button"
              className="btn btn-secondary text-xs"
              onClick={this.handleRetry}
            >
              <RotateCcw size={12} className="mr-1 inline-block" /> Retry
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}