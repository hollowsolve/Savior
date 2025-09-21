/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/**/*.{js,jsx,ts,tsx}',
    './public/index.html'
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        savior: {
          bg: '#0A0E1B',
          surface: '#12182E',
          'surface-2': '#1A2240',
          border: '#2A3458',
          'border-active': '#3B4A7C',
          red: '#EF3E36',
          'red-dim': '#8B2026',
          'red-glow': 'rgba(239, 62, 54, 0.2)',
        },
        accent: {
          blue: '#5E8AFF',
          green: '#3ECF8E',
          amber: '#F5A623',
          purple: '#B794F6',
          coral: '#ED5E5E',
        },
        text: {
          primary: '#FFFFFF',
          secondary: '#B8C4E6',
          tertiary: '#7986A8',
          disabled: '#4A5578',
        }
      },
      fontFamily: {
        display: ['Inter Display', 'system-ui', 'sans-serif'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'SF Mono', 'Monaco', 'monospace'],
      },
      fontSize: {
        'display-lg': '32px',
        'display-md': '24px',
        'display-sm': '20px',
      },
      animation: {
        'float': 'float 6s ease-in-out infinite',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'spin-slow': 'spin 3s linear infinite',
        'fade-in': 'fadeIn 0.3s ease-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'slide-down': 'slideDown 0.3s ease-out',
        'scale-in': 'scaleIn 0.2s ease-out',
        'shake': 'shake 0.5s ease-in-out',
        'glow-pulse': 'glowPulse 2s ease-in-out infinite',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-20px)' },
        },
        fadeIn: {
          from: { opacity: '0', transform: 'translateY(10px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        slideUp: {
          from: { transform: 'translateY(100%)' },
          to: { transform: 'translateY(0)' },
        },
        slideDown: {
          from: { transform: 'translateY(-100%)' },
          to: { transform: 'translateY(0)' },
        },
        scaleIn: {
          from: { transform: 'scale(0.9)', opacity: '0' },
          to: { transform: 'scale(1)', opacity: '1' },
        },
        shake: {
          '0%, 100%': { transform: 'translateX(0)' },
          '10%, 30%, 50%, 70%, 90%': { transform: 'translateX(-2px)' },
          '20%, 40%, 60%, 80%': { transform: 'translateX(2px)' },
        },
        glowPulse: {
          '0%, 100%': {
            filter: 'drop-shadow(0 0 20px rgba(239, 62, 54, 0.5))',
          },
          '50%': {
            filter: 'drop-shadow(0 0 30px rgba(239, 62, 54, 0.8))',
          },
        },
      },
      backdropBlur: {
        xs: '2px',
      },
      boxShadow: {
        'glow-sm': '0 0 10px rgba(239, 62, 54, 0.3)',
        'glow-md': '0 0 20px rgba(239, 62, 54, 0.4)',
        'glow-lg': '0 0 30px rgba(239, 62, 54, 0.5)',
        'glass': '0 8px 32px 0 rgba(31, 38, 135, 0.37)',
      },
    },
  },
  plugins: []
};