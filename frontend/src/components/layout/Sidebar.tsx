import React, { createContext, useContext, useState } from 'react'
import { NavLink, useLocation, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import useAuthStore from '../../state/auth'
import useRealtimeStore from '../../realtime/realtimeStore'

// ── Sidebar Context (shared collapse state) ───────────────────────────────────
interface SidebarContextValue {
  collapsed: boolean
  setCollapsed: (v: boolean) => void
}
export const SidebarContext = createContext<SidebarContextValue>({
  collapsed: false,
  setCollapsed: () => {},
})
export const useSidebar = () => useContext(SidebarContext)

// ── Nav structure ─────────────────────────────────────────────────────────────
interface NavItem {
  path: string
  label: string
  exact?: boolean
  icon: string
  liveIndicator?: boolean
}

const NAV_GROUPS: { label: string; items: NavItem[] }[] = [
  {
    label: 'Operations',
    items: [
      {
        path: '/app',
        label: 'Command Center',
        exact: true,
        icon: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6',
        liveIndicator: true,
      },
      {
        path: '/app/programs',
        label: 'Programs Control',
        icon: 'M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10',
      },
      {
        path: '/app/monitoring',
        label: 'Live Monitoring',
        icon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01',
        liveIndicator: true,
      },
    ],
  },
  {
    label: 'Intelligence',
    items: [
      {
        path: '/app/findings',
        label: 'Vulnerability Queue',
        icon: 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z',
        liveIndicator: true,
      },
      {
        path: '/app/graph',
        label: 'Attack Graph',
        icon: 'M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z',
      },
      {
        path: '/app/investigations',
        label: 'Investigations',
        icon: 'M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z',
      },
      {
        path: '/app/threat-intelligence',
        label: 'Threat Intelligence',
        icon: 'M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z',
      },
    ],
  },
  {
    label: 'Platform',
    items: [
      {
        path: '/app/reports',
        label: 'Reports & Ingest',
        icon: 'M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z',
      },
      {
        path: '/app/strategy',
        label: 'AI Strategy',
        icon: 'M13 10V3L4 14h7v7l9-11h-7z',
      },
      {
        path: '/app/marketplace',
        label: 'Scan Modules',
        icon: 'M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253',
      },
      {
        path: '/app/settings',
        label: 'Settings & Org',
        icon: 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z',
      },
    ],
  },
]

// ── Tooltip wrapper for collapsed mode ───────────────────────────────────────
const Tooltip: React.FC<{ label: string; children: React.ReactNode }> = ({ label, children }) => {
  const [show, setShow] = useState(false)
  return (
    <div className="relative" onMouseEnter={() => setShow(true)} onMouseLeave={() => setShow(false)}>
      {children}
      <AnimatePresence>
        {show && (
          <motion.div
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -8 }}
            className="absolute left-full top-1/2 -translate-y-1/2 ml-3 z-50 pointer-events-none"
          >
            <div className="bg-background-card border border-white/15 text-white text-xs font-medium px-3 py-1.5 rounded-lg whitespace-nowrap shadow-xl">
              {label}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

// ── NavItemRow ────────────────────────────────────────────────────────────────
const NavItemRow: React.FC<{ item: NavItem; collapsed: boolean; isConnected: boolean }> = ({
  item, collapsed, isConnected,
}) => {
  const location = useLocation()
  const isActive = item.exact
    ? location.pathname === item.path
    : location.pathname.startsWith(item.path)

  const inner = (
    <NavLink
      to={item.path}
      className={`relative flex items-center rounded-lg transition-all duration-200 group
        ${collapsed ? 'justify-center p-2.5' : 'px-3 py-2.5 gap-3'}
        ${isActive ? 'text-white' : 'text-gray-500 hover:text-gray-200 hover:bg-white/5'}
      `}
    >
      {/* Active background */}
      {isActive && (
        <motion.div
          layoutId="activeNavBg"
          className="absolute inset-0 bg-gradient-to-r from-primary/20 to-secondary/15 border border-primary/25 rounded-lg"
          style={{ boxShadow: '0 0 20px rgba(0,184,255,0.1), inset 0 1px 0 rgba(0,184,255,0.15)' }}
          initial={false}
          transition={{ type: 'spring', stiffness: 500, damping: 35 }}
        />
      )}

      {/* Icon */}
      <div className="relative z-10 shrink-0">
        <svg
          style={{ width: 16, height: 16 }}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          className={isActive ? 'text-primary' : 'text-current'}
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={isActive ? 2 : 1.5} d={item.icon} />
        </svg>
      </div>

      {/* Label */}
      {!collapsed && (
        <span className={`relative z-10 font-medium text-[13px] truncate ${isActive ? 'text-white' : ''}`}>
          {item.label}
        </span>
      )}

      {/* Live dot */}
      {item.liveIndicator && isConnected && !collapsed && (
        <div className="ml-auto relative z-10 w-1.5 h-1.5 rounded-full bg-emerald-400"
             style={{ boxShadow: '0 0 6px rgba(0,255,157,0.8)' }} />
      )}
      {item.liveIndicator && isConnected && collapsed && (
        <div className="absolute top-1 right-1 w-1.5 h-1.5 rounded-full bg-emerald-400"
             style={{ boxShadow: '0 0 6px rgba(0,255,157,0.8)' }} />
      )}
    </NavLink>
  )

  return collapsed ? <Tooltip label={item.label}>{inner}</Tooltip> : inner
}

// ── Main Sidebar ──────────────────────────────────────────────────────────────
const Sidebar: React.FC = () => {
  const navigate = useNavigate()
  const { user, clear, activeOrgId, organizations } = useAuthStore()
  const isConnected = useRealtimeStore((state) => state.isConnected)
  const activeAlerts = useRealtimeStore((state) => state.activeAlerts)
  const { collapsed, setCollapsed } = useSidebar()

  const activeOrg = organizations.find(o => o.id === activeOrgId)

  const handleLogout = () => {
    clear()
    navigate('/login')
  }

  return (
    <motion.aside
      animate={{ width: collapsed ? 64 : 220 }}
      transition={{ type: 'spring', stiffness: 400, damping: 35 }}
      className="h-screen border-r border-white/[0.07] flex flex-col z-20 shrink-0 overflow-hidden"
      style={{ background: 'linear-gradient(180deg, rgba(11,16,32,0.97) 0%, rgba(5,8,22,0.99) 100%)' }}
    >
      {/* ── Logo + Collapse toggle ── */}
      <div className={`flex items-center border-b border-white/[0.07] shrink-0 ${collapsed ? 'justify-center py-5' : 'px-5 h-16 justify-between'}`}>
        {!collapsed && (
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary to-secondary flex items-center justify-center shadow-glow-primary shrink-0">
              <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
            </div>
            <div>
              <div className="font-display font-bold text-sm text-gradient leading-tight">NisargHunter</div>
              <div className="text-[9px] text-gray-600 font-mono tracking-widest">CYBER OS v1.0</div>
            </div>
          </div>
        )}
        {collapsed && (
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary to-secondary flex items-center justify-center shadow-glow-primary">
            <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
          </div>
        )}
        {!collapsed && (
          <button
            onClick={() => setCollapsed(true)}
            className="text-gray-600 hover:text-gray-300 transition-colors p-1 rounded hover:bg-white/5"
            title="Collapse sidebar"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
            </svg>
          </button>
        )}
      </div>

      {/* ── Expand toggle (collapsed mode) ── */}
      {collapsed && (
        <button
          onClick={() => setCollapsed(false)}
          className="mx-auto mt-3 text-gray-600 hover:text-gray-300 transition-colors p-1.5 rounded hover:bg-white/5"
          title="Expand sidebar"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M13 5l7 7-7 7M5 5l7 7-7 7" />
          </svg>
        </button>
      )}

      {/* ── Nav groups ── */}
      <nav className={`flex-1 overflow-y-auto custom-scrollbar py-4 ${collapsed ? 'px-2 space-y-1' : 'px-3 space-y-1'}`}>
        {NAV_GROUPS.map((group) => (
          <div key={group.label} className={collapsed ? 'mb-4' : 'mb-5'}>
            {/* Group label — only when expanded */}
            {!collapsed && (
              <div className="px-3 mb-1.5">
                <span className="text-[9px] font-bold text-gray-700 uppercase tracking-[0.2em] font-mono">
                  {group.label}
                </span>
              </div>
            )}
            {/* Divider in collapsed mode */}
            {collapsed && <div className="w-6 h-px bg-white/10 mx-auto mb-2" />}

            <div className="space-y-0.5">
              {group.items.map((item) => (
                <NavItemRow key={item.path} item={item} collapsed={collapsed} isConnected={isConnected} />
              ))}
            </div>
          </div>
        ))}
      </nav>

      {/* ── Bottom: user + alerts + WS status ── */}
      <div className={`border-t border-white/[0.07] shrink-0 ${collapsed ? 'p-2' : 'p-3'}`}>
        {/* Alert count indicator */}
        {activeAlerts.length > 0 && !collapsed && (
          <div className="mb-2 px-3 py-2 bg-severity-critical/10 border border-severity-critical/20 rounded-lg flex items-center justify-between">
            <span className="text-xs text-severity-critical font-mono font-bold animate-pulse">
              {activeAlerts.length} ACTIVE ALERT{activeAlerts.length > 1 ? 'S' : ''}
            </span>
            <span className="text-[9px] text-severity-critical/60 font-mono">CRITICAL</span>
          </div>
        )}

        {/* User info (expanded only) */}
        {user && !collapsed && (
          <div className="flex items-center gap-2.5 px-3 py-2 rounded-lg bg-white/[0.03] border border-white/[0.07] mb-2">
            <div className="w-7 h-7 rounded-full bg-gradient-to-br from-primary to-secondary flex items-center justify-center text-xs font-bold text-white shrink-0">
              {user.username?.[0]?.toUpperCase() ?? 'U'}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-xs font-semibold text-white truncate">{user.username}</div>
              <div className="text-[10px] text-gray-500 truncate font-mono">{user.role ?? 'Operator'}</div>
            </div>
          </div>
        )}

        {/* WS status + logout */}
        <div className={`flex items-center ${collapsed ? 'justify-center' : 'justify-between px-1'}`}>
          {!collapsed && (
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-400' : 'bg-red-400'} animate-pulse`}
                   style={{ boxShadow: isConnected ? '0 0 8px rgba(74,222,128,0.8)' : '0 0 8px rgba(248,113,113,0.8)' }} />
              <span className="text-[10px] text-gray-500 font-mono">{isConnected ? 'REALTIME' : 'OFFLINE'}</span>
            </div>
          )}
          {collapsed && (
            <Tooltip label={isConnected ? 'Realtime Connected' : 'Sync Offline'}>
              <div className={`w-2.5 h-2.5 rounded-full ${isConnected ? 'bg-emerald-400' : 'bg-red-400'} animate-pulse`}
                   style={{ boxShadow: isConnected ? '0 0 8px rgba(74,222,128,0.8)' : '0 0 8px rgba(248,113,113,0.8)' }} />
            </Tooltip>
          )}
          {!collapsed && (
            <button
              onClick={handleLogout}
              className="text-gray-600 hover:text-red-400 transition-colors p-1.5 rounded hover:bg-red-500/10"
              title="Logout"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
              </svg>
            </button>
          )}
        </div>
      </div>
    </motion.aside>
  )
}

export { Sidebar as default }
