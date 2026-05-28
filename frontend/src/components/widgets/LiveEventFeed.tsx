import React, { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

// ── Event log entry types ─────────────────────────────────────────────────────
interface LogEvent {
  id: string
  type: string
  message?: string
  timestamp?: number | string
  correlation_id?: string
  data?: any
  payload?: any
  severity?: 'critical' | 'high' | 'medium' | 'low' | 'info'
}

const EVENT_COLORS: Record<string, string> = {
  finding_created:   'text-severity-critical',
  finding_triaged:   'text-severity-high',
  p1_alert:          'text-severity-critical',
  scan_started:      'text-primary',
  scan_completed:    'text-emerald-400',
  scan_progress:     'text-blue-400',
  ingestion_started: 'text-blue-400',
  ingestion_complete:'text-emerald-400',
  ingestion_error:   'text-red-400',
  h1_sync_started:   'text-sky-400',
  h1_sync_complete:  'text-emerald-400',
  h1_sync_error:     'text-red-400',
  monitoring_active: 'text-emerald-400',
  graph_generated:   'text-violet-400',
  ai_validated:      'text-purple-400',
  default:           'text-gray-400',
}

const getEventColor = (type: string) =>
  EVENT_COLORS[type?.toLowerCase()] ?? EVENT_COLORS.default

const getEventPrefix = (type: string): string => {
  if (type?.includes('error'))    return '[ERR]'
  if (type?.includes('critical')) return '[CRIT]'
  if (type?.includes('alert'))    return '[ALRT]'
  if (type?.includes('scan'))     return '[SCAN]'
  if (type?.includes('ingest'))   return '[INGEST]'
  if (type?.includes('h1'))       return '[H1]'
  if (type?.includes('finding'))  return '[FIND]'
  return '[SYS]'
}

// ── LiveEventFeed ─────────────────────────────────────────────────────────────
interface LiveEventFeedProps {
  events: LogEvent[]
  maxHeight?: string
  className?: string
  showEmpty?: boolean
}

export const LiveEventFeed: React.FC<LiveEventFeedProps> = ({
  events, maxHeight = '360px', className = '', showEmpty = true,
}) => {
  const containerRef = useRef<HTMLDivElement>(null)
  const [paused, setPaused] = useState(false)
  const [expanded, setExpanded] = useState<string | null>(null)

  // Auto-scroll to bottom when new events arrive
  useEffect(() => {
    if (!paused && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight
    }
  }, [events, paused])

  if (events.length === 0 && showEmpty) {
    return (
      <div className={`flex items-center justify-center ${className}`} style={{ minHeight: '120px' }}>
        <div className="text-center">
          <div className="text-gray-600 font-mono text-xs mb-1">&gt; SYSTEM IDLE</div>
          <div className="text-gray-700 font-mono text-[10px]">WAITING FOR WEBSOCKET PAYLOADS...</div>
          <div className="mt-2 flex justify-center gap-1">
            {[0,1,2].map(i => (
              <div key={i} className="w-1 h-1 rounded-full bg-primary/30 animate-pulse"
                   style={{ animationDelay: `${i * 0.2}s` }} />
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className={`flex flex-col ${className}`}>
      {/* Controls */}
      <div className="flex items-center justify-between mb-2 px-1">
        <div className="text-[10px] font-mono text-gray-600">
          {events.length} event{events.length !== 1 ? 's' : ''} captured
        </div>
        <button
          onClick={() => setPaused(p => !p)}
          className={`text-[10px] font-mono px-2 py-0.5 rounded border transition-colors ${
            paused
              ? 'border-yellow-500/30 text-yellow-400 bg-yellow-500/10'
              : 'border-white/10 text-gray-500 hover:text-white'
          }`}
        >
          {paused ? '▶ RESUME' : '⏸ PAUSE'}
        </button>
      </div>

      {/* Event log */}
      <div
        ref={containerRef}
        className="flex-1 overflow-y-auto custom-scrollbar space-y-1 font-mono text-[11px]"
        style={{ maxHeight }}
        onMouseEnter={() => setPaused(true)}
        onMouseLeave={() => setPaused(false)}
      >
        <AnimatePresence initial={false}>
          {events.map((evt, idx) => {
            const color = getEventColor(evt.type)
            const prefix = getEventPrefix(evt.type)
            const isExpanded = expanded === (evt.id || String(idx))
            const ts = evt.timestamp
              ? (typeof evt.timestamp === 'number'
                  ? new Date(evt.timestamp * 1000)
                  : new Date(evt.timestamp)
                ).toLocaleTimeString()
              : new Date().toLocaleTimeString()

            const payload = evt.data || evt.payload || {}
            const payloadStr = JSON.stringify(payload, null, 2)

            return (
              <motion.div
                key={evt.id || idx}
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="border-b border-white/[0.04] pb-1 hover:bg-white/[0.02] rounded px-1 cursor-pointer"
                onClick={() => setExpanded(isExpanded ? null : (evt.id || String(idx)))}
              >
                <div className="flex items-start gap-2">
                  <span className="text-gray-600 shrink-0 w-16 text-right">{ts}</span>
                  <span className={`font-bold shrink-0 ${color}`}>{prefix}</span>
                  <span className={`${color} font-semibold shrink-0`}>{evt.type?.toUpperCase()}</span>
                  <span className="text-gray-400 truncate flex-1">
                    {evt.message || String(payload?.message || payload?.title || '').slice(0, 80) || '—'}
                  </span>
                </div>
                {evt.correlation_id && (
                  <div className="text-[9px] text-primary/50 ml-20">trace:{evt.correlation_id}</div>
                )}
                <AnimatePresence>
                  {isExpanded && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      className="overflow-hidden"
                    >
                      <pre className="mt-1 ml-20 text-[10px] text-gray-500 bg-black/40 rounded p-2 overflow-x-auto whitespace-pre-wrap break-all max-h-32">
                        {payloadStr}
                      </pre>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            )
          })}
        </AnimatePresence>
      </div>
    </div>
  )
}

export default LiveEventFeed
