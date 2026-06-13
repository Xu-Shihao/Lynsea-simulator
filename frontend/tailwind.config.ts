import type { Config } from 'tailwindcss';

const config: Config = {
  darkMode: 'class',
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './lib/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // === Lynsea design tokens (docs/design/README.md) ===
        canvas: '#0B0F1A',        // app background (near-black navy)
        surface: {
          DEFAULT: '#141A29',     // cards / panels
          elevated: '#1B2336',    // popovers, raised cards
          dim: '#0a0e19',
          container: '#131929',
          'container-low': '#0e1320',
          'container-high': '#181f31',
          'container-highest': '#1d253a',
          variant: '#1d253a',
          bright: '#232b43',
        },
        border: '#2A3346',        // card borders
        'grid-hairline': '#1F2738',
        // Text
        'text-primary': '#E6EAF2',
        'text-secondary': '#98A2B8',
        'text-muted': '#5F6B82',
        // Brand colors
        primary: {
          DEFAULT: '#8B7CF6',     // indigo — neutral actions, focus ring, CTA
          dim: '#9d8fff',
          fixed: '#c2b9ff',
          container: '#9182fd',
        },
        // Branch colors — NEVER swap A/B
        'branch-a': '#22D3EE',    // cyan — Branch A always left
        'branch-b': '#FBBF24',    // amber — Branch B always right
        'branch-c': '#A78BFA',    // violet — what-if (P1)
        fork: '#F472B6',          // magenta — divergence marker
        shared: '#94A3B8',        // slate — shared/perturbation events
        // Metric deltas
        positive: '#34D399',
        negative: '#FB7185',
        // Other surface/outline tokens used in stitch HTML
        outline: {
          DEFAULT: '#6d758e',
          variant: '#40475e',
        },
        'on-surface': '#dee5ff',
        'on-surface-variant': '#a3aac5',
        'on-primary': '#1f0078',
        'on-primary-fixed': '#230086',
        'on-primary-container': '#11004e',
        secondary: {
          DEFAULT: '#2fd9f4',
          container: '#002a31',
          dim: '#00cbe6',
        },
        'on-secondary': '#004752',
        'on-secondary-container': '#00b4cc',
        tertiary: {
          DEFAULT: '#ffd16f',
          container: '#fcc025',
          dim: '#edb210',
        },
        error: {
          DEFAULT: '#fd6f85',
          container: '#8a1632',
          dim: '#c8475d',
        },
        'on-error': '#490013',
        // Brand-prefixed aliases (from dashboard html)
        'brand-cyan': '#22D3EE',
        'brand-amber': '#FBBF24',
        'brand-magenta': '#F472B6',
        'brand-navy': '#0B0F1A',
      },
      fontFamily: {
        display: ['Space Grotesk', 'sans-serif'],
        headline: ['Space Grotesk', 'sans-serif'],
        title: ['Space Grotesk', 'sans-serif'],
        body: ['Inter', 'sans-serif'],
        label: ['Inter', 'sans-serif'],
        caption: ['Inter', 'sans-serif'],
        'data-numeric': ['Inter', 'sans-serif'],
      },
      fontSize: {
        display: ['40px', { lineHeight: '48px', letterSpacing: '-0.02em', fontWeight: '700' }],
        headline: ['28px', { lineHeight: '36px', fontWeight: '600' }],
        title: ['20px', { lineHeight: '28px', fontWeight: '500' }],
        body: ['16px', { lineHeight: '24px', fontWeight: '400' }],
        label: ['14px', { lineHeight: '20px', fontWeight: '500' }],
        caption: ['12px', { lineHeight: '16px', fontWeight: '400' }],
        'data-numeric': ['14px', { lineHeight: '20px', letterSpacing: '0.05em', fontWeight: '600' }],
      },
      borderRadius: {
        DEFAULT: '0.25rem',
        card: '8px',
        panel: '12px',
        pill: '9999px',
        lg: '0.5rem',
        xl: '0.75rem',
        full: '9999px',
      },
      spacing: {
        xs: '4px',
        sm: '8px',
        md: '16px',
        lg: '24px',
        xl: '40px',
        margin: '32px',
        gutter: '24px',
        unit: '4px',
      },
      boxShadow: {
        'glow-primary': '0 0 20px rgba(139, 124, 246, 0.4)',
        'glow-cyan': '0 0 15px rgba(34, 211, 238, 0.2)',
        'glow-amber': '0 0 15px rgba(251, 191, 36, 0.2)',
        'glow-magenta': '0 0 15px rgba(244, 114, 182, 0.4)',
      },
    },
  },
  plugins: [],
};

export default config;
