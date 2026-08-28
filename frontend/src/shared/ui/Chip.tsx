'use client';

import React from 'react';
import { Severity } from '@/types/api';

export interface ChipProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'critical' | 'warning' | 'info' | 'success' | 'neutral' | 'outline' | Severity;
  children: React.ReactNode;
}

export const Chip: React.FC<ChipProps> = ({
  variant = 'neutral',
  children,
  className = '',
  ...props
}) => {
  const getVariantClass = () => {
    switch (variant) {
      case 'HIGH':
      case 'critical':
        return 'chip-critical';
      case 'MEDIUM':
      case 'warning':
        return 'chip-warning';
      case 'LOW':
      case 'info':
        return 'chip-info';
      case 'success':
        return 'chip-success';
      case 'outline':
        return 'bg-white border border-border text-slate-700';
      default:
        return 'chip-neutral';
    }
  };

  return (
    <span className={`chip ${getVariantClass()} ${className}`} {...props}>
      {children}
    </span>
  );
};
