/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        void: '#0A0E14',
        panel: '#10151F',
        'panel-raised': '#141B27',
        hairline: '#1E2836',
        signal: {
          amber: '#F5A623',
          'amber-dim': '#8A5D14',
          danger: '#E5484D',
          safe: '#2DD4BF',
        },
        ink: {
          primary: '#E8EAED',
          muted: '#7C8798',
          faint: '#4B5563',
        },
      },
      fontFamily: {
        display: ['"Space Grotesk"', 'sans-serif'],
        body: ['"Inter"', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      backgroundImage: {
        'grid-lines':
          'linear-gradient(to right, rgba(30,40,54,0.5) 1px, transparent 1px), linear-gradient(to bottom, rgba(30,40,54,0.5) 1px, transparent 1px)',
      },
      backgroundSize: {
        grid: '40px 40px',
      },
      animation: {
        scan: 'scan 4s linear infinite',
        blip: 'blip 3s ease-in-out infinite',
        'pulse-ring': 'pulse-ring 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        scan: {
          '0%': { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(100%)' },
        },
        blip: {
          '0%, 100%': { opacity: 0.3, transform: 'scale(0.9)' },
          '50%': { opacity: 1, transform: 'scale(1.1)' },
        },
        'pulse-ring': {
          '0%': { transform: 'scale(0.8)', opacity: 0.8 },
          '100%': { transform: 'scale(2.2)', opacity: 0 },
        },
      },
    },
  },
  plugins: [],
}
