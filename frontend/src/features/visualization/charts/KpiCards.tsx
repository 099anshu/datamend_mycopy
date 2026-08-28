'use client';

import React from 'react';
import { Activity, AlertCircle, ShieldCheck, TrendingDown } from 'lucide-react';
import { AnomalyItem, TimestampScore } from '@/types/api';

interface KpiCardsProps {
  scores: TimestampScore[];
  anomalies: AnomalyItem[];
  missingRate?: number;
  missingValueHandling?: string;
}

export const KpiCards: React.FC<KpiCardsProps> = ({
  scores,
  anomalies,
  missingRate,
  missingValueHandling,
}) => {
  const totalPoints = scores.length;
  const totalAnomalies = anomalies.length;
  const highSeverity = anomalies.filter((a) => a.severity === 'HIGH').length;
  const medSeverity = anomalies.filter((a) => a.severity === 'MEDIUM').length;
  const lowSeverity = anomalies.filter((a) => a.severity === 'LOW').length;
  const anomalyPercentage =
    totalPoints > 0 ? ((totalAnomalies / totalPoints) * 100).toFixed(2) : '0.00';

  const cards = [
    {
      title: 'Time Series Length',
      value: totalPoints > 0 ? `${totalPoints.toLocaleString()} steps` : '—',
      sub:
        totalPoints > 0
          ? `${Object.keys(scores[0]?.values || {}).length} dimensions`
          : 'Awaiting data',
      color: '#1a56c4',
    },
    {
      title: 'Detected Anomalies',
      value: totalAnomalies.toLocaleString(),
      sub:
        totalAnomalies > 0
          ? `${highSeverity}H · ${medSeverity}M · ${lowSeverity}L`
          : '0 incidents detected',
      color: totalAnomalies > 0 ? '#d32f2f' : '#2e7d32',
    },
    {
      title: 'Anomaly Density',
      value: `${anomalyPercentage}%`,
      sub: totalAnomalies > 0 ? 'Of analyzed sequence' : 'Baseline state',
      color: totalAnomalies > 0 ? '#d32f2f' : '#1a56c4',
      icon: TrendingDown,
    },
    {
      title: 'Corruption & Imputation',
      value:
        typeof missingRate === 'number'
          ? `${(missingRate * 100).toFixed(1)}% NaNs`
          : '0.0% clean',
      sub: missingValueHandling
        ? `Strategy: ${missingValueHandling}`
        : 'Strategy: reject',
      color:
        typeof missingRate === 'number' && missingRate > 0 ? '#e69100' : '#2e7d32',
      icon: ShieldCheck,
    },
  ];

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(1rem, 1fr))',
        gap: 12,
      }}
    >
      {cards.map((card, idx) => {
        const Icon = card.icon;
        return (
          <div
            key={idx}
            className="panel"
            style={{
              padding: '.7rem',
              display: 'flex',
              alignItems: 'flex-start',
              justifyContent: 'space-between',
            }}
          >
            <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <span
                style={{
                  fontSize: '0.8rem',
                  fontWeight: 500,
                  textTransform: 'uppercase',
                  color: '#64748b',
                }}
              >
                {card.title}
              </span>
              <span
                className="tabular-nums"
                style={{
                  fontSize: '1rem',
                  fontWeight: 500,
                  color: card.color,
                }}
              >
                {card.value}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
};
