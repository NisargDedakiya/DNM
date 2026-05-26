/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: {
          DEFAULT: '#050816',
          paper: '#0B1020',
          card: '#111827',
        },
        primary: {
          DEFAULT: '#00B8FF',
          dark: '#008CFF',
        },
        secondary: {
          DEFAULT: '#9D4DFF',
          dark: '#7A3CFF',
        },
        accent: {
          blue: '#00B8FF',
          purple: '#9D4DFF',
        },
        severity: {
          critical: '#FF0055',
          high: '#FF8A00',
          medium: '#FFD600',
          low: '#00B8FF',
          info: '#9D4DFF',
        }
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        mono: ['Fira Code', 'monospace'],
      },
      animation: {
        'gradient-x': 'gradient-x 15s ease infinite',
        'gradient-y': 'gradient-y 15s ease infinite',
        'gradient-xy': 'gradient-xy 15s ease infinite',
        'pulse-glow': 'pulse-glow 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'typing': 'typing 2s steps(20, end)',
        'float': 'float 6s ease-in-out infinite',
      },
      keyframes: {
        'gradient-y': {
          '0%, 100%': {
            'background-size': '400% 400%',
            'background-position': 'center top'
          },
          '50%': {
            'background-size': '200% 200%',
            'background-position': 'center center'
          }
        },
        'gradient-x': {
          '0%, 100%': {
            'background-size': '200% 200%',
            'background-position': 'left center'
          },
          '50%': {
            'background-size': '200% 200%',
            'background-position': 'right center'
          }
        },
        'gradient-xy': {
          '0%, 100%': {
            'background-size': '400% 400%',
            'background-position': 'left center'
          },
          '50%': {
            'background-size': '200% 200%',
            'background-position': 'right center'
          }
        },
        'pulse-glow': {
          '0%, 100%': {
            opacity: 1,
            boxShadow: '0 0 15px rgba(0, 184, 255, 0.5)',
          },
          '50%': {
            opacity: .8,
            boxShadow: '0 0 25px rgba(157, 77, 255, 0.8)',
          }
        },
        'typing': {
          from: { width: '0' },
          to: { width: '100%' }
        },
        'float': {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-10px)' }
        }
      }
    },
  },
  plugins: [],
}
