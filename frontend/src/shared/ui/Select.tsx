'use client';

import React from 'react';

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
}

export const Select: React.FC<SelectProps> = ({ label, className = '', id, children, ...props }) => {
  return (
    <div className="form-group mb-0">
      {label && (
        <label htmlFor={id} className="form-label">
          {label}
        </label>
      )}
      <select id={id} className={`form-select ${className}`} {...props}>
        {children}
      </select>
    </div>
  );
};
