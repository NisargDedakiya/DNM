import React from 'react';
import { motion } from 'framer-motion';

// ── Card ─────────────────────────────────────────────────────
interface CardProps {
  children: React.ReactNode;
  className?: string;
  glowHover?: boolean;
}

export const Card: React.FC<CardProps> = ({ children, className = '', glowHover = false }) => {
  return (
    <div className={`relative group ${className}`}>
      {glowHover && (
        <div className="absolute -inset-[1px] bg-gradient-to-r from-primary to-secondary rounded-xl opacity-0 group-hover:opacity-100 blur-[2px] transition-opacity duration-500"></div>
      )}
      <div className={`relative h-full glass-card p-6 ${glowHover ? 'group-hover:border-transparent' : ''} transition-colors duration-300`}>
        {children}
      </div>
    </div>
  );
};

// ── Badge ─────────────────────────────────────────────────────
export type BadgeVariant = 'primary' | 'secondary' | 'critical' | 'high' | 'medium' | 'low' | 'info' | 'outline' | 'success';

interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  className?: string;
}

const BADGE_VARIANTS: Record<BadgeVariant, string> = {
  primary:   'bg-primary/20 text-primary border-primary/30 shadow-[0_0_10px_rgba(0,184,255,0.2)]',
  secondary: 'bg-secondary/20 text-secondary border-secondary/30 shadow-[0_0_10px_rgba(157,77,255,0.2)]',
  critical:  'bg-[#FF0055]/20 text-[#FF0055] border-[#FF0055]/30 shadow-[0_0_10px_rgba(255,0,85,0.2)]',
  high:      'bg-[#FF8A00]/20 text-[#FF8A00] border-[#FF8A00]/30 shadow-[0_0_10px_rgba(255,138,0,0.2)]',
  medium:    'bg-[#FFD600]/20 text-[#FFD600] border-[#FFD600]/30 shadow-[0_0_10px_rgba(255,214,0,0.2)]',
  low:       'bg-[#00B8FF]/20 text-[#00B8FF] border-[#00B8FF]/30 shadow-[0_0_10px_rgba(0,184,255,0.2)]',
  info:      'bg-[#9D4DFF]/20 text-[#9D4DFF] border-[#9D4DFF]/30 shadow-[0_0_10px_rgba(157,77,255,0.2)]',
  outline:   'bg-transparent text-gray-300 border-white/20',
  success:   'bg-green-500/20 text-green-400 border-green-500/30 shadow-[0_0_10px_rgba(74,222,128,0.15)]',
};

export const Badge: React.FC<BadgeProps> = ({ children, variant = 'primary', className = '' }) => {
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border ${BADGE_VARIANTS[variant]} ${className}`}>
      {children}
    </span>
  );
};

// ── Button ─────────────────────────────────────────────────────
interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'critical' | 'danger';
  glow?: boolean;
}

const BUTTON_VARIANTS: Record<string, string> = {
  primary:   'bg-gradient-to-r from-primary to-primary-dark text-white border border-white/10 hover:border-white/20 hover:shadow-[0_0_20px_rgba(0,184,255,0.4)]',
  secondary: 'bg-gradient-to-r from-secondary to-secondary-dark text-white border border-white/10 hover:border-white/20 hover:shadow-[0_0_20px_rgba(157,77,255,0.4)]',
  outline:   'bg-transparent text-white border border-white/20 hover:bg-white/5',
  ghost:     'bg-transparent text-gray-300 hover:text-white hover:bg-white/5 border border-transparent',
  critical:  'bg-[#FF0055]/20 text-[#FF0055] border border-[#FF0055]/30 hover:bg-[#FF0055]/30',
  danger:    'bg-red-600 text-white border border-red-500/50 hover:bg-red-700',
};

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'primary',
  glow = true,
  className = '',
  disabled,
  ...props
}) => {
  const baseStyles = 'relative inline-flex items-center justify-center px-6 py-2.5 text-sm font-semibold rounded-lg transition-all duration-300 overflow-hidden disabled:opacity-50 disabled:cursor-not-allowed';
  return (
    <motion.button
      whileHover={disabled ? {} : { scale: 1.02 }}
      whileTap={disabled ? {} : { scale: 0.98 }}
      className={`${baseStyles} ${BUTTON_VARIANTS[variant] ?? BUTTON_VARIANTS.primary} ${className}`}
      disabled={disabled}
      {...(props as any)}
    >
      <span className="relative z-10">{children}</span>
    </motion.button>
  );
};

// ── Spinner ────────────────────────────────────────────────────
export const Spinner: React.FC<{ className?: string }> = ({ className = 'w-5 h-5' }) => (
  <svg className={`animate-spin ${className}`} xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
  </svg>
);

// ── EmptyState ─────────────────────────────────────────────────
export const EmptyState: React.FC<{ icon?: string; title: string; subtitle?: string }> = ({ title, subtitle }) => (
  <div className="flex flex-col items-center justify-center py-16 text-center">
    <div className="w-16 h-16 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center mb-4">
      <svg className="w-8 h-8 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
      </svg>
    </div>
    <h3 className="text-white font-semibold mb-2">{title}</h3>
    {subtitle && <p className="text-gray-400 text-sm max-w-sm">{subtitle}</p>}
  </div>
);
