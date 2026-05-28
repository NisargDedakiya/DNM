import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

// ── Card ─────────────────────────────────────────────────────────────────────
interface CardProps {
  children: React.ReactNode;
  className?: string;
  glowHover?: boolean;
  cyber?: boolean;
}

export const Card: React.FC<CardProps> = ({ children, className = '', glowHover = false, cyber = false }) => {
  if (cyber) {
    return (
      <div className={`cyber-panel corner-accent ${className}`}>
        {children}
      </div>
    );
  }
  return (
    <div className={`relative group ${className}`}>
      {glowHover && (
        <div className="absolute -inset-[1px] bg-gradient-to-r from-primary to-secondary rounded-xl opacity-0 group-hover:opacity-70 blur-[3px] transition-opacity duration-500" />
      )}
      <div className={`relative h-full glass-card p-6 ${glowHover ? 'group-hover:border-transparent' : ''} transition-colors duration-300`}>
        {children}
      </div>
    </div>
  );
};

// ── Badge ─────────────────────────────────────────────────────────────────────
export type BadgeVariant = 'primary' | 'secondary' | 'critical' | 'high' | 'medium' | 'low' | 'info' | 'outline' | 'success' | 'warning' | 'nominal';

interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  className?: string;
  pulse?: boolean;
}

const BADGE_VARIANTS: Record<BadgeVariant, string> = {
  primary:   'bg-primary/15 text-primary border-primary/30 shadow-[0_0_12px_rgba(0,184,255,0.2)]',
  secondary: 'bg-secondary/15 text-secondary border-secondary/30 shadow-[0_0_12px_rgba(157,77,255,0.2)]',
  critical:  'bg-[#FF0055]/15 text-[#FF0055] border-[#FF0055]/30 shadow-[0_0_12px_rgba(255,0,85,0.25)]',
  high:      'bg-[#FF8A00]/15 text-[#FF8A00] border-[#FF8A00]/30 shadow-[0_0_12px_rgba(255,138,0,0.2)]',
  medium:    'bg-[#FFD600]/15 text-[#FFD600] border-[#FFD600]/30 shadow-[0_0_12px_rgba(255,214,0,0.2)]',
  low:       'bg-[#00B8FF]/15 text-[#00B8FF] border-[#00B8FF]/30 shadow-[0_0_12px_rgba(0,184,255,0.2)]',
  info:      'bg-[#9D4DFF]/15 text-[#9D4DFF] border-[#9D4DFF]/30 shadow-[0_0_12px_rgba(157,77,255,0.2)]',
  outline:   'bg-transparent text-gray-300 border-white/20',
  success:   'bg-green-500/15 text-green-400 border-green-500/30 shadow-[0_0_12px_rgba(74,222,128,0.2)]',
  warning:   'bg-yellow-500/15 text-yellow-400 border-yellow-500/30',
  nominal:   'bg-emerald-500/15 text-emerald-400 border-emerald-500/30 shadow-[0_0_12px_rgba(0,255,157,0.2)]',
};

export const Badge: React.FC<BadgeProps> = ({ children, variant = 'primary', className = '', pulse = false }) => (
  <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${BADGE_VARIANTS[variant]} ${className}`}>
    {pulse && <span className="w-1.5 h-1.5 rounded-full bg-current animate-ping inline-block" />}
    {children}
  </span>
);

// ── Button ─────────────────────────────────────────────────────────────────────
interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'critical' | 'danger' | 'success';
  glow?: boolean;
  size?: 'xs' | 'sm' | 'md' | 'lg';
  loading?: boolean;
}

const BUTTON_VARIANTS: Record<string, string> = {
  primary:   'bg-gradient-to-r from-primary to-primary-dark text-white border border-primary/20 hover:border-primary/40 hover:shadow-glow-primary',
  secondary: 'bg-gradient-to-r from-secondary to-secondary-dark text-white border border-secondary/20 hover:border-secondary/40 hover:shadow-glow-secondary',
  outline:   'bg-transparent text-white border border-white/20 hover:bg-white/5 hover:border-white/30',
  ghost:     'bg-transparent text-gray-300 hover:text-white hover:bg-white/5 border border-transparent',
  critical:  'bg-severity-critical/15 text-severity-critical border border-severity-critical/30 hover:bg-severity-critical/25 hover:shadow-glow-critical',
  danger:    'bg-red-600 text-white border border-red-500/50 hover:bg-red-700',
  success:   'bg-green-600/20 text-green-400 border border-green-500/30 hover:bg-green-600/30',
};

const BUTTON_SIZES: Record<string, string> = {
  xs: 'px-3 py-1 text-xs',
  sm: 'px-4 py-1.5 text-xs',
  md: 'px-6 py-2.5 text-sm',
  lg: 'px-8 py-3 text-base',
};

export const Button: React.FC<ButtonProps> = ({
  children, variant = 'primary', glow = true, className = '',
  disabled, size = 'md', loading = false, ...props
}) => (
  <motion.button
    whileHover={disabled || loading ? {} : { scale: 1.02 }}
    whileTap={disabled || loading ? {} : { scale: 0.97 }}
    className={`relative inline-flex items-center justify-center font-semibold rounded-lg transition-all duration-300 overflow-hidden disabled:opacity-50 disabled:cursor-not-allowed ${BUTTON_SIZES[size]} ${BUTTON_VARIANTS[variant] ?? BUTTON_VARIANTS.primary} ${className}`}
    disabled={disabled || loading}
    {...(props as any)}
  >
    <span className="relative z-10 flex items-center gap-2">
      {loading && (
        <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      )}
      {children}
    </span>
  </motion.button>
);

// ── Spinner ─────────────────────────────────────────────────────────────────
export const Spinner: React.FC<{ className?: string; color?: string }> = ({
  className = 'w-5 h-5', color = 'text-primary'
}) => (
  <svg className={`animate-spin ${color} ${className}`} xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
  </svg>
);

// ── EmptyState ──────────────────────────────────────────────────────────────
export const EmptyState: React.FC<{
  icon?: React.ReactNode;
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
}> = ({ icon, title, subtitle, action }) => (
  <div className="flex flex-col items-center justify-center py-16 text-center">
    <div className="w-16 h-16 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center mb-5">
      {icon || (
        <svg className="w-8 h-8 text-primary/60" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
        </svg>
      )}
    </div>
    <h3 className="text-white font-semibold font-display mb-2">{title}</h3>
    {subtitle && <p className="text-gray-400 text-sm max-w-sm">{subtitle}</p>}
    {action && <div className="mt-5">{action}</div>}
  </div>
);

// ── TelemetryCard ────────────────────────────────────────────────────────────
interface TelemetryCardProps {
  label: string;
  value: string | number;
  delta?: string;
  deltaPositive?: boolean;
  color?: 'primary' | 'critical' | 'high' | 'medium' | 'green' | 'secondary';
  icon?: React.ReactNode;
  suffix?: string;
  className?: string;
  live?: boolean;
}

const TELEMETRY_COLORS = {
  primary:   { text: 'text-primary',             bg: 'bg-primary/10',     border: 'border-primary/15',   glow: 'shadow-[0_0_20px_rgba(0,184,255,0.08)]' },
  critical:  { text: 'text-severity-critical',    bg: 'bg-severity-critical/10', border: 'border-severity-critical/15', glow: 'shadow-[0_0_20px_rgba(255,0,85,0.08)]' },
  high:      { text: 'text-severity-high',        bg: 'bg-severity-high/10',     border: 'border-severity-high/15',     glow: 'shadow-[0_0_20px_rgba(255,138,0,0.08)]' },
  medium:    { text: 'text-severity-medium',      bg: 'bg-severity-medium/10',   border: 'border-severity-medium/15',   glow: 'shadow-[0_0_20px_rgba(255,214,0,0.08)]' },
  green:     { text: 'text-emerald-400',          bg: 'bg-emerald-500/10',       border: 'border-emerald-500/15',       glow: 'shadow-[0_0_20px_rgba(0,255,157,0.08)]' },
  secondary: { text: 'text-secondary',            bg: 'bg-secondary/10',         border: 'border-secondary/15',         glow: 'shadow-[0_0_20px_rgba(157,77,255,0.08)]' },
};

export const TelemetryCard: React.FC<TelemetryCardProps> = ({
  label, value, delta, deltaPositive, color = 'primary', icon, suffix, className = '', live = false,
}) => {
  const c = TELEMETRY_COLORS[color];
  const [displayValue, setDisplayValue] = useState(0);
  const numValue = typeof value === 'number' ? value : parseFloat(String(value)) || 0;

  useEffect(() => {
    let start = 0;
    const end = numValue;
    if (end === 0) { setDisplayValue(0); return; }
    const duration = 600;
    const step = (timestamp: number) => {
      if (start === 0) start = timestamp;
      const progress = Math.min((timestamp - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplayValue(Math.floor(eased * end));
      if (progress < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }, [numValue]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className={`relative rounded-xl border ${c.border} ${c.bg} ${c.glow} p-5 overflow-hidden group hover:scale-[1.01] transition-transform duration-300 ${className}`}
    >
      {/* Background decoration */}
      <div className={`absolute top-2 right-2 opacity-[0.07] scale-150 ${c.text}`}>{icon}</div>

      <div className="flex items-start justify-between mb-3">
        <div className={`text-[10px] uppercase tracking-widest font-bold ${c.text} opacity-70`}>{label}</div>
        {live && <div className="live-indicator text-[10px]">LIVE</div>}
      </div>

      <div className={`text-3xl font-display font-bold ${c.text} animate-counter-up`}>
        {typeof value === 'number' ? displayValue.toLocaleString() : value}
        {suffix && <span className="text-lg ml-1 opacity-70">{suffix}</span>}
      </div>

      {delta && (
        <div className={`text-xs font-mono mt-2 ${deltaPositive ? 'text-emerald-400' : 'text-rose-400'}`}>
          {deltaPositive ? '▲' : '▼'} {delta}
        </div>
      )}
    </motion.div>
  );
};

// ── StatusIndicator ──────────────────────────────────────────────────────────
export const StatusIndicator: React.FC<{
  status: 'live' | 'offline' | 'degraded' | 'connecting';
  label?: string;
  className?: string;
}> = ({ status, label, className = '' }) => {
  const configs = {
    live:       { dot: 'bg-green-400',  shadow: 'shadow-[0_0_8px_rgba(74,222,128,0.8)]',   text: 'text-green-400',  ping: 'bg-green-400' },
    offline:    { dot: 'bg-red-400',    shadow: 'shadow-[0_0_8px_rgba(248,113,113,0.8)]',  text: 'text-red-400',    ping: 'bg-red-400' },
    degraded:   { dot: 'bg-yellow-400', shadow: 'shadow-[0_0_8px_rgba(250,204,21,0.8)]',   text: 'text-yellow-400', ping: 'bg-yellow-400' },
    connecting: { dot: 'bg-blue-400',   shadow: 'shadow-[0_0_8px_rgba(96,165,250,0.8)]',   text: 'text-blue-400',   ping: 'bg-blue-400' },
  };
  const c = configs[status];
  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <div className="relative flex h-2.5 w-2.5">
        <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${c.ping} opacity-50`} />
        <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${c.dot} ${c.shadow}`} />
      </div>
      {label && <span className={`text-xs font-mono font-medium ${c.text}`}>{label}</span>}
    </div>
  );
};

// ── SeverityBar ──────────────────────────────────────────────────────────────
export const SeverityBar: React.FC<{
  critical: number; high: number; medium: number; low: number; total: number;
}> = ({ critical, high, medium, low, total }) => {
  if (total === 0) return null;
  return (
    <div className="flex rounded-full overflow-hidden h-1.5 w-full gap-px">
      {critical > 0 && <div className="bg-severity-critical" style={{ width: `${(critical/total)*100}%` }} />}
      {high > 0     && <div className="bg-severity-high"     style={{ width: `${(high/total)*100}%` }} />}
      {medium > 0   && <div className="bg-severity-medium"   style={{ width: `${(medium/total)*100}%` }} />}
      {low > 0      && <div className="bg-severity-low"      style={{ width: `${(low/total)*100}%` }} />}
    </div>
  );
};

// ── CyberPanel ───────────────────────────────────────────────────────────────
export const CyberPanel: React.FC<{
  children: React.ReactNode;
  title?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
  scanLine?: boolean;
  headerClass?: string;
}> = ({ children, title, action, className = '', scanLine = false, headerClass = '' }) => (
  <div className={`cyber-panel ${scanLine ? 'scan-line-overlay' : ''} ${className}`}>
    {(title || action) && (
      <div className={`flex items-center justify-between px-5 py-3.5 border-b border-white/5 ${headerClass}`}>
        <div className="flex items-center gap-2">{title}</div>
        {action}
      </div>
    )}
    {children}
  </div>
);

// ── PanelHeader helper ────────────────────────────────────────────────────────
export const PanelLabel: React.FC<{
  dot?: 'primary' | 'green' | 'red' | 'yellow';
  children: React.ReactNode;
}> = ({ dot, children }) => {
  const dotColors = {
    primary: 'bg-primary', green: 'bg-green-400', red: 'bg-red-400', yellow: 'bg-yellow-400',
  };
  return (
    <div className="flex items-center gap-2">
      {dot && (
        <span className="relative flex h-2 w-2">
          <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${dotColors[dot]} opacity-60`} />
          <span className={`relative inline-flex rounded-full h-2 w-2 ${dotColors[dot]}`} />
        </span>
      )}
      <span className="text-xs uppercase font-bold tracking-widest text-gray-400 font-mono">{children}</span>
    </div>
  );
};
