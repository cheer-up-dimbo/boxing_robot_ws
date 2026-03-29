/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{vue,js,ts,jsx,tsx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        bb: {
          bg: '#0D0D0D',
          surface: '#1A1A1A',
          'surface-light': '#242424',
          'surface-lighter': '#2E2E2E',
          green: '#00E676',
          'green-dark': '#00C853',
          'green-dim': '#00E67620',
          warning: '#FF9800',
          'warning-dim': '#FF980020',
          danger: '#FF1744',
          'danger-dim': '#FF174420',
          text: '#FFFFFF',
          'text-secondary': '#9E9E9E',
          'text-muted': '#616161',
          border: '#333333',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-out',
        'slide-up': 'slideUp 0.4s ease-out',
        'slide-down': 'slideDown 0.3s ease-out',
        'scale-in': 'scaleIn 0.3s ease-out',
        'pulse-glow': 'pulseGlow 2s ease-in-out infinite',
        'flame': 'flame 1.5s ease-in-out infinite alternate',
        'count-up': 'countUp 0.6s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideDown: {
          '0%': { opacity: '0', transform: 'translateY(-10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        scaleIn: {
          '0%': { opacity: '0', transform: 'scale(0.9)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
        pulseGlow: {
          '0%, 100%': { boxShadow: '0 0 5px rgba(0, 230, 118, 0.3)' },
          '50%': { boxShadow: '0 0 20px rgba(0, 230, 118, 0.6)' },
        },
        flame: {
          '0%': { transform: 'scale(1) rotate(-3deg)', opacity: '0.8' },
          '100%': { transform: 'scale(1.1) rotate(3deg)', opacity: '1' },
        },
        countUp: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
  ],
}
