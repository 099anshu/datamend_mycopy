'use client';

import React from 'react';

export interface PanelProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'title'> {
  title?: React.ReactNode;
  subtitle?: React.ReactNode;
  headerActions?: React.ReactNode;
  icon?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  bodyClassName?: string;
}

export const Panel: React.FC<PanelProps> = ({
  title,
  subtitle,
  headerActions,
  icon,
  children,
  className = '',
  bodyClassName = '',
  style,
  ...props
}) => {
  return (
    <div className={`panel ${className}`} style={style} {...props}>
      {title && (
        <div className="panel-header">
          <div>
            <div className="panel-header-title">
              {icon}
              <span>{title}</span>
            </div>
            {subtitle && (
              <div className="panel-header-subtitle">{subtitle}</div>
            )}
          </div>
          {headerActions && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              {headerActions}
            </div>
          )}
        </div>
      )}
      <div className={`panel-body ${bodyClassName}`}>{children}</div>
    </div>
  );
};
