import React from 'react'
import { motion } from 'framer-motion'

// ── DEFCON / Threat Level Display ─────────────────────────────────────────────
const THREAT_LEVELS = [
  { level: 5, label: 'NOMINAL',    color: '#00FF9D', desc: 'No active threats detected.' },
  { level: 4, label: 'GUARDED',    color: '#00B8FF', desc: 'Low-level indicators observed.' },
  { level: 3, label: 'ELEVATED',   color: '#FFD600', desc: 'Active threats in scope.' },
  { level: 2, label: 'HIGH ALERT', color: '#FF8A00', desc: 'Critical exposure detected.' },
  { level: 1, label: 'CRITICAL',   color: '#FF0055', desc: 'Immediate action required.' },
]

interface ThreatLevelBarProps {
  level?: 1 | 2 | 3 | 4 | 5
  criticalCount?: number
  highCount?: number
  className?: string
}

export const ThreatLevelBar: React.FC<ThreatLevelBarProps> = ({
  level = 5,
  criticalCount = 0,
  highCount = 0,
  className = '',
}) => {
  // Auto-derive level from counts if not provided explicitly
  const derivedLevel = level !== 5
    ? level
    : criticalCount > 0 ? 1
    : highCount > 5     ? 2
    : highCount > 0     ? 3
    : 5

  const current = THREAT_LEVELS.find(t => t.level === derivedLevel) ?? THREAT_LEVELS[0]
  const isActive = derivedLevel <= 3

  return (
    <div className={`flex items-center gap-4 ${className}`}>
      {/* DEFCON blocks */}
      <div className="flex items-center gap-1">
        <span className="text-[9px] text-gray-600 font-mono uppercase tracking-widest mr-2">DEFCON</span>
        {[1,2,3,4,5].map(n => {
          const t = THREAT_LEVELS.find(t => t.level === n)!
          const isCurrentOrWorse = n >= derivedLevel
          return (
            <motion.div
              key={n}
              animate={n === derivedLevel && isActive
                ? { boxShadow: [`0 0 6px ${t.color}60`, `0 0 14px ${t.color}`, `0 0 6px ${t.color}60`] }
                : { boxShadow: 'none' }
              }
              transition={{ repeat: Infinity, duration: 1.5 }}
              title={`DEFCON ${n}: ${t.label}`}
              className="w-7 h-7 rounded flex items-center justify-center text-[10px] font-bold font-mono border transition-all"
              style={{
                borderColor: isCurrentOrWorse ? `${t.color}60` : 'rgba(255,255,255,0.08)',
                backgroundColor: n === derivedLevel ? `${t.color}22` : isCurrentOrWorse ? `${t.color}08` : 'transparent',
                color: isCurrentOrWorse ? t.color : 'rgba(255,255,255,0.2)',
              }}
            >
              {n}
            </motion.div>
          )
        })}
      </div>

      {/* Current level label */}
      <div className="flex items-center gap-2">
        {isActive && (
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-60" style={{ background: current.color }} />
            <span className="relative inline-flex rounded-full h-2 w-2" style={{ background: current.color }} />
          </span>
        )}
        <div>
          <div className="text-xs font-bold font-mono" style={{ color: current.color }}>
            {current.label}
          </div>
          <div className="text-[9px] text-gray-600 font-mono">{current.desc}</div>
        </div>
      </div>
    </div>
  )
}

// ── AttackPathCard ─────────────────────────────────────────────────────────────
interface AttackNode {
  id: string
  label: string
  type: 'entry' | 'lateral' | 'pivot' | 'target' | 'exfil'
}

interface AttackPathCardProps {
  title: string
  nodes: AttackNode[]
  severity: 'critical' | 'high' | 'medium' | 'low'
  affectedTargets?: number
  discoveredAt?: string
  className?: string
}

const NODE_COLORS = {
  entry:   { bg: 'bg-severity-critical/15',  border: 'border-severity-critical/30',  text: 'text-severity-critical',  icon: '⚡' },
  lateral: { bg: 'bg-severity-high/15',      border: 'border-severity-high/30',      text: 'text-severity-high',      icon: '↔' },
  pivot:   { bg: 'bg-severity-medium/15',    border: 'border-severity-medium/30',    text: 'text-severity-medium',    icon: '◆' },
  target:  { bg: 'bg-primary/15',            border: 'border-primary/30',            text: 'text-primary',            icon: '🎯' },
  exfil:   { bg: 'bg-secondary/15',          border: 'border-secondary/30',          text: 'text-secondary',          icon: '⬆' },
}

const SEVERITY_BORDER = {
  critical: 'border-severity-critical/25',
  high:     'border-severity-high/25',
  medium:   'border-severity-medium/25',
  low:      'border-severity-low/25',
}

export const AttackPathCard: React.FC<AttackPathCardProps> = ({
  title, nodes, severity, affectedTargets, discoveredAt, className = '',
}) => (
  <motion.div
    initial={{ opacity: 0, y: 10 }}
    animate={{ opacity: 1, y: 0 }}
    className={`rounded-xl border ${SEVERITY_BORDER[severity]} bg-white/[0.02] p-4 hover:bg-white/[0.035] transition-colors ${className}`}
  >
    <div className="flex items-start justify-between mb-4">
      <div>
        <div className="text-sm font-bold text-white font-display">{title}</div>
        {discoveredAt && (
          <div className="text-[10px] text-gray-500 font-mono mt-0.5">
            Discovered: {new Date(discoveredAt).toLocaleDateString()}
          </div>
        )}
      </div>
      {affectedTargets !== undefined && (
        <div className="text-center">
          <div className="text-lg font-bold text-white">{affectedTargets}</div>
          <div className="text-[9px] text-gray-500 uppercase font-mono">Targets</div>
        </div>
      )}
    </div>

    {/* Kill chain nodes */}
    <div className="flex items-center gap-1 flex-wrap">
      {nodes.map((node, i) => {
        const c = NODE_COLORS[node.type]
        return (
          <React.Fragment key={node.id}>
            <div className={`flex items-center gap-1 px-2 py-1 rounded text-[10px] font-mono font-semibold border ${c.bg} ${c.border} ${c.text}`}>
              <span>{c.icon}</span>
              <span>{node.label}</span>
            </div>
            {i < nodes.length - 1 && (
              <span className="text-gray-600 text-xs">→</span>
            )}
          </React.Fragment>
        )
      })}
    </div>
  </motion.div>
)

// ── AIInsightPanel ─────────────────────────────────────────────────────────────
interface AIInsight {
  id: string
  title: string
  body: string
  confidence: number   // 0-100
  urgency: 'critical' | 'high' | 'medium' | 'low'
  category: 'attack-path' | 'remediation' | 'recon' | 'escalation'
  timestamp?: string
}

interface AIInsightPanelProps {
  insights: AIInsight[]
  className?: string
}

const URGENCY_COLORS = {
  critical: { text: 'text-severity-critical', bg: 'bg-severity-critical/10', border: 'border-severity-critical/20' },
  high:     { text: 'text-severity-high',     bg: 'bg-severity-high/10',     border: 'border-severity-high/20' },
  medium:   { text: 'text-severity-medium',   bg: 'bg-severity-medium/10',   border: 'border-severity-medium/20' },
  low:      { text: 'text-primary',           bg: 'bg-primary/10',           border: 'border-primary/20' },
}

const CATEGORY_ICONS = {
  'attack-path': '🕸',
  'remediation': '🛠',
  'recon':       '🔍',
  'escalation':  '⬆',
}

export const AIInsightPanel: React.FC<AIInsightPanelProps> = ({ insights, className = '' }) => (
  <div className={`space-y-3 ${className}`}>
    {insights.length === 0 && (
      <div className="py-8 text-center text-gray-600 text-sm font-mono">
        AI reasoning engine warming up...
      </div>
    )}
    {insights.map((insight, i) => {
      const c = URGENCY_COLORS[insight.urgency]
      return (
        <motion.div
          key={insight.id}
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: i * 0.08 }}
          className={`rounded-xl border ${c.border} ${c.bg} p-4`}
        >
          <div className="flex items-start justify-between gap-3 mb-2">
            <div className="flex items-center gap-2">
              <span className="text-base">{CATEGORY_ICONS[insight.category]}</span>
              <div className={`text-xs font-bold ${c.text}`}>{insight.title}</div>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              {/* Confidence gauge */}
              <div className="flex items-center gap-1.5">
                <div className="w-16 h-1 bg-white/10 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${insight.confidence >= 80 ? 'bg-emerald-400' : insight.confidence >= 50 ? 'bg-yellow-400' : 'bg-red-400'}`}
                    style={{ width: `${insight.confidence}%` }}
                  />
                </div>
                <span className="text-[9px] font-mono text-gray-500">{insight.confidence}%</span>
              </div>
            </div>
          </div>
          <p className="text-xs text-gray-400 leading-relaxed">{insight.body}</p>
          {insight.timestamp && (
            <div className="text-[9px] text-gray-600 font-mono mt-2">
              {new Date(insight.timestamp).toLocaleTimeString()}
            </div>
          )}
        </motion.div>
      )
    })}
  </div>
)

export default ThreatLevelBar
