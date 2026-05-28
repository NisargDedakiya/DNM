import React, { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import Sidebar, { SidebarContext } from './Sidebar'
import Navbar from './Navbar'
import useRealtimeStore from '../../realtime/realtimeStore'

// ── Global Critical Alert Toast ───────────────────────────────────────────────
const CriticalAlertToast: React.FC = () => {
  const activeAlerts = useRealtimeStore((s) => s.activeAlerts)
  const [dismissed, setDismissed] = useState<Set<string>>(new Set())

  const visibleAlerts = activeAlerts.filter(a => !dismissed.has(a.id || a.correlation_id || String(a)))
  const latest = visibleAlerts[0]

  const dismiss = () => {
    const key = latest?.id || latest?.correlation_id || String(latest)
    if (key) setDismissed(d => new Set([...d, key]))
  }

  return (
    <AnimatePresence>
      {latest && (
        <motion.div
          key={latest.id || latest.correlation_id}
          initial={{ opacity: 0, y: -60, scale: 0.9 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -20, scale: 0.95 }}
          className="fixed top-4 right-4 z-[100] w-96 rounded-xl border border-severity-critical/50 overflow-hidden"
          style={{
            background: 'rgba(10,5,18,0.97)',
            boxShadow: '0 0 30px rgba(255,0,85,0.3), 0 0 0 1px rgba(255,0,85,0.2)',
            backdropFilter: 'blur(20px)',
          }}
        >
          {/* Animated top border */}
          <div className="h-0.5 bg-gradient-to-r from-severity-critical via-severity-high to-severity-critical animate-border-pulse" />

          <div className="p-4">
            <div className="flex items-start justify-between mb-2">
              <div className="flex items-center gap-2">
                <span className="relative flex h-2.5 w-2.5">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-severity-critical opacity-75" />
                  <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-severity-critical" />
                </span>
                <span className="text-[10px] uppercase font-mono tracking-[0.2em] text-severity-critical font-bold">
                  CRITICAL INCIDENT DETECTED
                </span>
              </div>
              <button
                onClick={dismiss}
                className="text-gray-600 hover:text-white transition-colors text-lg leading-none"
              >×</button>
            </div>
            <p className="text-sm text-white font-semibold font-mono mt-1">
              {latest.title || latest.description || latest.message || 'Critical threat indicator observed.'}
            </p>
            {latest.correlation_id && (
              <p className="text-[10px] text-gray-600 font-mono mt-2">
                Trace: {latest.correlation_id}
              </p>
            )}
            {visibleAlerts.length > 1 && (
              <p className="text-[10px] text-severity-critical/60 font-mono mt-1">
                +{visibleAlerts.length - 1} more critical alert{visibleAlerts.length > 2 ? 's' : ''}
              </p>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

// ── MainLayout ────────────────────────────────────────────────────────────────
const MainLayout: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false)

  return (
    <SidebarContext.Provider value={{ collapsed, setCollapsed }}>
      <div className="flex h-screen overflow-hidden" style={{ background: '#050816' }}>

        {/* ── Background layers ── */}
        {/* Deep cyber grid */}
        <div
          className="fixed inset-0 z-0 pointer-events-none"
          style={{
            backgroundImage: 'linear-gradient(rgba(0,184,255,0.025) 1px, transparent 1px), linear-gradient(90deg, rgba(0,184,255,0.025) 1px, transparent 1px)',
            backgroundSize: '48px 48px',
          }}
        />
        {/* Radial gradient center */}
        <div
          className="fixed inset-0 z-0 pointer-events-none"
          style={{
            background: 'radial-gradient(ellipse 80% 50% at 50% 0%, rgba(0,184,255,0.06) 0%, transparent 70%)',
          }}
        />
        {/* Ambient glow orbs */}
        <div className="fixed top-[-15%] left-[-5%] w-[35%] h-[40%] rounded-full bg-primary/8 blur-[100px] pointer-events-none z-0 animate-pulse-glow" />
        <div className="fixed bottom-[-15%] right-[-5%] w-[35%] h-[40%] rounded-full bg-secondary/8 blur-[100px] pointer-events-none z-0 animate-pulse-glow" style={{ animationDelay: '1.5s' }} />

        {/* ── Layout ── */}
        <Sidebar />
        <div className="flex-1 flex flex-col relative z-10 overflow-hidden min-w-0">
          <Navbar />
          <main className="flex-1 overflow-y-auto custom-scrollbar">
            <div className="p-6 min-h-full">
              <Outlet />
            </div>
          </main>
        </div>

        {/* ── Global critical alert toast ── */}
        <CriticalAlertToast />
      </div>
    </SidebarContext.Provider>
  )
}

export default MainLayout
