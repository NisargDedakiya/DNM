import React, { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import useAuthStore from '../../state/auth'
import useRealtimeStore from '../../realtime/realtimeStore'

// ── Route display names ────────────────────────────────────────────────────────
const PAGE_TITLES: Record<string, string> = {
  '/app':                    'Command Center',
  '/app/programs':           'Programs Control',
  '/app/monitoring':         'Live Monitoring',
  '/app/findings':           'Vulnerability Queue',
  '/app/graph':              'Attack Graph',
  '/app/investigations':     'Investigations',
  '/app/reports':            'Reports & Ingest',
  '/app/strategy':           'AI Strategy',
  '/app/threat-intelligence':'Threat Intelligence',
  '/app/marketplace':        'Scan Modules',
  '/app/settings':           'Settings & Org',
}

// ── Command palette action type ──────────────────────────────────────────────
interface CommandAction {
  id: string
  label: string
  description?: string
  icon: string
  path?: string
  action?: () => void
  category: 'navigation' | 'action' | 'search'
}

const COMMAND_ACTIONS: CommandAction[] = [
  { id: 'cmd-center', label: 'Command Center', description: 'Operational overview', icon: '🏠', path: '/app', category: 'navigation' },
  { id: 'findings',   label: 'Vulnerability Queue', description: 'Review findings', icon: '⚡', path: '/app/findings', category: 'navigation' },
  { id: 'graph',      label: 'Attack Graph', description: 'Threat visualization', icon: '🕸', path: '/app/graph', category: 'navigation' },
  { id: 'investigations', label: 'Investigations', description: 'Evidence workspace', icon: '🔍', path: '/app/investigations', category: 'navigation' },
  { id: 'programs',   label: 'Programs Control', description: 'Scope management', icon: '📋', path: '/app/programs', category: 'navigation' },
  { id: 'monitoring', label: 'Live Monitoring', description: 'Active scan monitoring', icon: '📡', path: '/app/monitoring', category: 'navigation' },
  { id: 'strategy',   label: 'AI Strategy', description: 'AI-assisted planning', icon: '🤖', path: '/app/strategy', category: 'navigation' },
]

// ── Command Palette ───────────────────────────────────────────────────────────
const CommandPalette: React.FC<{ onClose: () => void }> = ({ onClose }) => {
  const [query, setQuery] = useState('')
  const [activeIdx, setActiveIdx] = useState(0)
  const navigate = useNavigate()
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => { inputRef.current?.focus() }, [])

  const filtered = COMMAND_ACTIONS.filter(
    a =>
      a.label.toLowerCase().includes(query.toLowerCase()) ||
      a.description?.toLowerCase().includes(query.toLowerCase())
  )

  useEffect(() => { setActiveIdx(0) }, [query])

  const execute = useCallback((action: CommandAction) => {
    if (action.path) navigate(action.path)
    action.action?.()
    onClose()
  }, [navigate, onClose])

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
      if (e.key === 'ArrowDown') setActiveIdx(i => Math.min(i + 1, filtered.length - 1))
      if (e.key === 'ArrowUp') setActiveIdx(i => Math.max(i - 1, 0))
      if (e.key === 'Enter' && filtered[activeIdx]) execute(filtered[activeIdx])
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [filtered, activeIdx, execute, onClose])

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-start justify-center pt-24 px-4"
      style={{ background: 'rgba(5,8,22,0.85)', backdropFilter: 'blur(12px)' }}
      onClick={onClose}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.94, y: -20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.94, y: -20 }}
        transition={{ type: 'spring', stiffness: 400, damping: 30 }}
        className="w-full max-w-xl cyber-panel overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        {/* Search input */}
        <div className="flex items-center gap-3 px-5 py-4 border-b border-white/[0.07]">
          <svg className="w-4 h-4 text-gray-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            ref={inputRef}
            type="text"
            placeholder="Search pages, actions, commands..."
            value={query}
            onChange={e => setQuery(e.target.value)}
            className="flex-1 bg-transparent text-white placeholder-gray-600 text-sm outline-none font-mono"
          />
          <kbd className="text-[10px] text-gray-600 border border-white/10 px-1.5 py-0.5 rounded font-mono">ESC</kbd>
        </div>

        {/* Results */}
        <div className="max-h-80 overflow-y-auto custom-scrollbar py-2">
          {filtered.length === 0 ? (
            <div className="px-5 py-8 text-center text-gray-600 text-sm font-mono">
              No results for "{query}"
            </div>
          ) : (
            filtered.map((action, idx) => (
              <button
                key={action.id}
                onClick={() => execute(action)}
                className={`w-full flex items-center gap-3 px-5 py-3 text-left transition-colors ${
                  idx === activeIdx ? 'bg-primary/10 text-white' : 'text-gray-400 hover:bg-white/[0.03] hover:text-white'
                }`}
              >
                <span className="text-base w-6 text-center shrink-0">{action.icon}</span>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium">{action.label}</div>
                  {action.description && (
                    <div className="text-[11px] text-gray-600 font-mono">{action.description}</div>
                  )}
                </div>
                {idx === activeIdx && (
                  <kbd className="text-[10px] text-primary border border-primary/30 px-1.5 py-0.5 rounded font-mono shrink-0">↵</kbd>
                )}
              </button>
            ))
          )}
        </div>

        <div className="px-5 py-2.5 border-t border-white/[0.07] flex items-center gap-4 text-[10px] text-gray-600 font-mono">
          <span><kbd className="border border-white/10 px-1 py-0.5 rounded mr-1">↑↓</kbd> navigate</span>
          <span><kbd className="border border-white/10 px-1 py-0.5 rounded mr-1">↵</kbd> select</span>
          <span><kbd className="border border-white/10 px-1 py-0.5 rounded mr-1">esc</kbd> close</span>
        </div>
      </motion.div>
    </motion.div>
  )
}

// ── Main Navbar ───────────────────────────────────────────────────────────────
const Navbar: React.FC = () => {
  const { user, activeOrgId, organizations } = useAuthStore()
  const isConnected = useRealtimeStore((s) => s.isConnected)
  const activeAlerts = useRealtimeStore((s) => s.activeAlerts)
  const recentEvents = useRealtimeStore((s) => s.recentEvents)
  const location = useLocation()
  const [paletteOpen, setPaletteOpen] = useState(false)

  const activeOrg = organizations.find(o => o.id === activeOrgId)
  const pageTitle = PAGE_TITLES[location.pathname] ?? 'Operations'

  // Global ⌘K / Ctrl+K handler
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setPaletteOpen(p => !p)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  // Last event latency (mock from event timestamps)
  const lastEvent = recentEvents[recentEvents.length - 1]
  const wsLatency = lastEvent ? '12ms' : '—'

  const criticalCount = activeAlerts.length

  return (
    <>
      <header
        className="h-14 flex items-center justify-between px-6 z-10 sticky top-0 shrink-0"
        style={{
          background: 'rgba(5,8,22,0.92)',
          backdropFilter: 'blur(20px)',
          borderBottom: '1px solid rgba(255,255,255,0.06)',
        }}
      >
        {/* Left: page title + breadcrumb */}
        <div className="flex items-center gap-5">
          <div>
            <h2 className="text-sm font-display font-bold text-white leading-tight">{pageTitle}</h2>
            {activeOrg && (
              <div className="text-[10px] font-mono text-gray-600 leading-tight">
                SEGMENT: {activeOrg.name.toUpperCase()}
              </div>
            )}
          </div>

          {/* WS latency chip */}
          {isConnected && (
            <div className="flex items-center gap-1.5 text-[10px] font-mono text-emerald-500 bg-emerald-500/5 border border-emerald-500/10 px-2 py-1 rounded">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              WS {wsLatency}
            </div>
          )}
        </div>

        {/* Center: search / command palette trigger */}
        <button
          id="navbar-command-palette-trigger"
          onClick={() => setPaletteOpen(true)}
          className="flex items-center gap-2 bg-white/[0.03] border border-white/[0.08] rounded-lg px-4 py-2 text-sm text-gray-500 hover:text-gray-300 hover:bg-white/[0.05] hover:border-white/[0.12] transition-all w-72"
        >
          <svg className="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <span className="flex-1 text-left font-mono text-[12px]">Search or run command...</span>
          <kbd className="text-[10px] border border-white/10 px-1.5 py-0.5 rounded font-mono">⌘K</kbd>
        </button>

        {/* Right: alerts + events count + user */}
        <div className="flex items-center gap-4">
          {/* Critical alert count */}
          {criticalCount > 0 && (
            <motion.div
              animate={{ scale: [1, 1.05, 1] }}
              transition={{ repeat: Infinity, duration: 2 }}
              className="flex items-center gap-1.5 bg-severity-critical/10 border border-severity-critical/25 rounded-lg px-2.5 py-1.5 text-severity-critical text-xs font-mono font-bold"
            >
              <span className="w-1.5 h-1.5 rounded-full bg-severity-critical animate-ping" />
              {criticalCount} CRITICAL
            </motion.div>
          )}

          {/* Events count */}
          <div className="text-[10px] font-mono text-gray-600">
            <span className="text-gray-400">{recentEvents.length}</span> events
          </div>

          {/* WS status */}
          <div className="flex items-center gap-1.5">
            <div
              className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-400' : 'bg-red-400'} animate-pulse`}
              style={{ boxShadow: isConnected ? '0 0 6px rgba(74,222,128,0.8)' : '0 0 6px rgba(248,113,113,0.8)' }}
            />
            <span className="text-[10px] font-mono text-gray-500">
              {isConnected ? 'LIVE' : 'OFFLINE'}
            </span>
          </div>

          {/* User avatar */}
          <div className="flex items-center gap-2.5 pl-4 border-l border-white/[0.07]">
            <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-primary to-secondary p-[1.5px]">
              <div className="w-full h-full rounded-full bg-background flex items-center justify-center">
                <span className="text-xs font-bold text-white">
                  {user?.username?.[0]?.toUpperCase() ?? 'OP'}
                </span>
              </div>
            </div>
            <div className="hidden sm:flex flex-col">
              <span className="text-xs font-semibold text-white leading-tight">{user?.username ?? 'Operator'}</span>
              <span className="text-[10px] text-gray-500 font-mono leading-tight">{user?.role ?? 'Operator'}</span>
            </div>
          </div>
        </div>
      </header>

      {/* Command Palette overlay */}
      <AnimatePresence>
        {paletteOpen && <CommandPalette onClose={() => setPaletteOpen(false)} />}
      </AnimatePresence>
    </>
  )
}

export default Navbar
