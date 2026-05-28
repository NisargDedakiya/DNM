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
          card: '#0D1424',
          surface: '#111827',
        },
        primary: {
          DEFAULT: '#00B8FF',
          dark: '#008CFF',
          muted: 'rgba(0,184,255,0.15)',
        },
        secondary: {
          DEFAULT: '#9D4DFF',
          dark: '#7A3CFF',
          muted: 'rgba(157,77,255,0.15)',
        },
        accent: {
          cyan: '#00B8FF',
          purple: '#9D4DFF',
          green: '#00FF9D',
          orange: '#FF8A00',
        },
        severity: {
          critical: '#FF0055',
          high: '#FF8A00',
          medium: '#FFD600',
          low: '#00B8FF',
          info: '#9D4DFF',
          nominal: '#00FF9D',
        },
        // Semantic operational states
        threat: {
          critical: '#FF0055',
          high:     '#FF8A00',
          medium:   '#FFD600',
          low:      '#00B8FF',
          nominal:  '#00FF9D',
        },
        surface: {
          1: 'rgba(255,255,255,0.02)',
          2: 'rgba(255,255,255,0.04)',
          3: 'rgba(255,255,255,0.07)',
          4: 'rgba(255,255,255,0.10)',
        },
      },
      fontFamily: {
        sans:     ['Inter', 'sans-serif'],
        display:  ['Space Grotesk', 'Inter', 'sans-serif'],
        mono:     ['JetBrains Mono', 'Fira Code', 'monospace'],
        terminal: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      boxShadow: {
        'glow-primary':   '0 0 15px rgba(0,184,255,0.4), 0 0 40px rgba(0,184,255,0.1)',
        'glow-secondary': '0 0 15px rgba(157,77,255,0.4), 0 0 40px rgba(157,77,255,0.1)',
        'glow-critical':  '0 0 15px rgba(255,0,85,0.4), 0 0 40px rgba(255,0,85,0.1)',
        'glow-green':     '0 0 15px rgba(0,255,157,0.4), 0 0 40px rgba(0,255,157,0.1)',
        'panel':          '0 8px 32px rgba(0,0,0,0.6), 0 1px 0 rgba(255,255,255,0.05)',
        'card':           '0 4px 16px rgba(0,0,0,0.4)',
        'cyber':          'inset 0 1px 0 rgba(0,184,255,0.1), 0 0 20px rgba(0,184,255,0.05)',
      },
      animation: {
        'gradient-x':     'gradient-x 15s ease infinite',
        'pulse-glow':     'pulse-glow 2s cubic-bezier(0.4,0,0.6,1) infinite',
        'data-flow':      'data-flow 3s linear infinite',
        'radar-sweep':    'radar-sweep 4s linear infinite',
        'matrix-fade':    'matrix-fade 2s ease-in-out infinite',
        'scan-line':      'scan-line 8s linear infinite',
        'border-flow':    'border-flow 3s linear infinite',
        'counter-up':     'counter-up 0.6s cubic-bezier(0.34,1.56,0.64,1)',
        'slide-in-right': 'slide-in-right 0.3s cubic-bezier(0.34,1.56,0.64,1)',
        'slide-in-up':    'slide-in-up 0.3s cubic-bezier(0.34,1.56,0.64,1)',
        'fade-in':        'fade-in 0.25s ease-out',
        'terminal-blink': 'terminal-blink 1s step-end infinite',
        'float':          'float 6s ease-in-out infinite',
        'ping-slow':      'ping 2s cubic-bezier(0,0,0.2,1) infinite',
      },
      keyframes: {
        'gradient-x': {
          '0%,100%': { 'background-position': 'left center', 'background-size': '200% 200%' },
          '50%':      { 'background-position': 'right center', 'background-size': '200% 200%' },
        },
        'pulse-glow': {
          '0%,100%': { opacity: '1', boxShadow: '0 0 15px rgba(0,184,255,0.5)' },
          '50%':      { opacity: '.8', boxShadow: '0 0 30px rgba(157,77,255,0.8)' },
        },
        'data-flow': {
          '0%':   { transform: 'translateY(100%)' },
          '100%': { transform: 'translateY(-100%)' },
        },
        'radar-sweep': {
          '0%':   { transform: 'rotate(0deg)' },
          '100%': { transform: 'rotate(360deg)' },
        },
        'matrix-fade': {
          '0%,100%': { opacity: '0.15' },
          '50%':     { opacity: '0.4' },
        },
        'scan-line': {
          '0%':   { top: '-5%' },
          '100%': { top: '105%' },
        },
        'border-flow': {
          '0%':   { 'background-position': '0% 50%' },
          '50%':  { 'background-position': '100% 50%' },
          '100%': { 'background-position': '0% 50%' },
        },
        'counter-up': {
          '0%':   { transform: 'translateY(20px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        'slide-in-right': {
          '0%':   { transform: 'translateX(30px)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' },
        },
        'slide-in-up': {
          '0%':   { transform: 'translateY(20px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        'fade-in': {
          '0%':   { opacity: '0' },
          '100%': { opacity: '1' },
        },
        'terminal-blink': {
          '0%,100%': { opacity: '1' },
          '50%':     { opacity: '0' },
        },
        'float': {
          '0%,100%': { transform: 'translateY(0)' },
          '50%':     { transform: 'translateY(-8px)' },
        },
      },
      backgroundImage: {
        'cyber-grid': "linear-gradient(rgba(0,184,255,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(0,184,255,0.03) 1px, transparent 1px)",
        'hex-pattern': "url(\"data:image/svg+xml,%3Csvg width='60' height='60' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M30 5L55 20v30L30 65 5 50V20z' fill='none' stroke='rgba(0,184,255,0.04)' stroke-width='1'/%3E%3C/svg%3E\")",
        'gradient-radial': 'radial-gradient(ellipse at center, var(--tw-gradient-stops))',
      },
      backgroundSize: {
        'cyber-grid': '40px 40px',
        'hex-pattern': '60px 60px',
      },
    },
  },
  plugins: [],
}
