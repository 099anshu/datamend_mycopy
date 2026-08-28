import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/features/**/*.{js,ts,jsx,tsx,mdx}',
    './src/shared/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        page: '#eef0f3',
        panel: {
          DEFAULT: '#ffffff',
          header: '#1c4b5a',
          hover: '#153843',
        },
        border: {
          DEFAULT: '#d7dbe0',
          subtle: '#e5e7eb',
        },
        brand: {
          DEFAULT: '#1a56c4',
          hover: '#144296',
        },
        status: {
          critical: '#d32f2f',
          'critical-bg': '#fee2e2',
          warning: '#e69100',
          'warning-bg': '#fef3c7',
          info: '#1a56c4',
          'info-bg': '#dbeafe',
          success: '#2e7d32',
          'success-bg': '#dcfce7',
        },
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      boxShadow: {
        panel: '0 1px 2px rgba(0, 0, 0, 0.04)',
      },
      borderRadius: {
        DEFAULT: '6px',
        panel: '6px',
      },
    },
  },
  plugins: [],
};

export default config;
