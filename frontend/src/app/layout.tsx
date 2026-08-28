import type { Metadata } from 'next';
import './globals.css';
import { QueryProvider } from '@/shared/providers/QueryProvider';

export const metadata: Metadata = {
  title: 'DataMend | Intelligent Time-Series Anomaly Detection',
  description:
    'Time-series anomaly detection dashboard powered by TimeRCD zero-shot inference, PyGrinder corruption simulation, and ECharts visualization.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <QueryProvider>
          <div className="relative min-h-screen flex flex-col">{children}</div>
        </QueryProvider>
      </body>
    </html>
  );
}
