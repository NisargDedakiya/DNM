import React, { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import websocketManager from '../../realtime/websocketManager'

// ─── Types ──────────────────────────────────────────────────────────────────

export type PipelineStage =
  | 'ingestion_started'
  | 'page_fetched'
  | 'scope_extracted'
  | 'ai_validated'
  | 'targets_normalized'
  | 'graph_generated'
  | 'monitoring_active'
  | 'findings_active'
  | 'ingestion_complete'
  | 'ingestion_error'
  // HackerOne
  | 'h1_sync_started'
  | 'h1_programs_fetched'
  | 'h1_scope_normalized'
  | 'h1_reports_synced'
  | 'h1_sync_complete'
  | 'h1_sync_error'

interface StageEvent {
  stage: PipelineStage
  message: string
  timestamp: number
  payload?: Record<string, any>
}

interface StageConfig {
  id: PipelineStage
  label: string
  icon: string
  color: string
}

// ─── Bugcrowd Pipeline Stages ────────────────────────────────────────────────

const BUGCROWD_STAGES: StageConfig[] = [
  { id: 'ingestion_started', label: 'Ingestion Started', icon: '⚡', color: 'text-blue-400' },
  { id: 'page_fetched',      label: 'Page Fetched',     icon: '🌐', color: 'text-cyan-400' },
  { id: 'scope_extracted',   label: 'Scope Extracted',  icon: '📋', color: 'text-violet-400' },
  { id: 'ai_validated',      label: 'AI Validated',     icon: '🤖', color: 'text-purple-400' },
  { id: 'targets_normalized',label: 'Targets Normalized',icon: '🎯', color: 'text-indigo-400' },
  { id: 'graph_generated',   label: 'Graph Generated',  icon: '🕸️', color: 'text-amber-400' },
  { id: 'monitoring_active', label: 'Monitoring Active',icon: '📡', color: 'text-green-400' },
  { id: 'findings_active',   label: 'Findings Pipeline',icon: '🔍', color: 'text-emerald-400' },
  { id: 'ingestion_complete',label: 'Complete',          icon: '✅', color: 'text-green-300' },
]

// ─── HackerOne Pipeline Stages ───────────────────────────────────────────────

const H1_STAGES: StageConfig[] = [
  { id: 'h1_sync_started',      label: 'Sync Started',         icon: '⚡', color: 'text-sky-400' },
  { id: 'h1_programs_fetched',  label: 'Programs Fetched',     icon: '📥', color: 'text-blue-400' },
  { id: 'h1_scope_normalized',  label: 'Scopes Normalized',    icon: '🎯', color: 'text-violet-400' },
  { id: 'h1_reports_synced',    label: 'Reports Synced',       icon: '📊', color: 'text-purple-400' },
  { id: 'h1_sync_complete',     label: 'Sync Complete',        icon: '✅', color: 'text-green-300' },
]

// ─── All stage event types to subscribe to ──────────────────────────────────

const ALL_STAGE_EVENTS: PipelineStage[] = [
  'ingestion_started', 'page_fetched', 'scope_extracted', 'ai_validated',
  'targets_normalized', 'graph_generated', 'monitoring_active', 'findings_active',
  'ingestion_complete', 'ingestion_error',
  'h1_sync_started', 'h1_programs_fetched', 'h1_scope_normalized',
  'h1_reports_synced', 'h1_sync_complete', 'h1_sync_error',
]

// ─── StageRow Component ──────────────────────────────────────────────────────

const StageRow: React.FC<{
  config: StageConfig
  isActive: boolean
  isCompleted: boolean
  isError: boolean
  event?: StageEvent
}> = ({ config, isActive, isCompleted, isError, event }) => {
  return (
    <motion.div
      initial={{ opacity: 0.4 }}
      animate={{ opacity: isActive || isCompleted ? 1 : 0.35 }}
      className={`flex items-start gap-3 py-3 px-4 rounded-xl border transition-all duration-500 ${
        isError
          ? 'border-red-500/30 bg-red-500/5'
          : isActive
          ? 'border-primary/40 bg-primary/5'
          : isCompleted
          ? 'border-green-500/25 bg-green-500/5'
          : 'border-white/5 bg-transparent'
      }`}
    >
      {/* Status Indicator */}
      <div className="mt-0.5 flex-shrink-0 w-6 h-6 flex items-center justify-center">
        {isError ? (
          <span className="text-red-400 text-sm">✕</span>
        ) : isActive ? (
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ repeat: Infinity, duration: 1.2, ease: 'linear' }}
            className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full"
          />
        ) : isCompleted ? (
          <motion.span
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: 'spring', stiffness: 400 }}
            className="text-green-400 text-sm"
          >
            ✓
          </motion.span>
        ) : (
          <div className="w-4 h-4 border-2 border-white/10 rounded-full" />
        )}
      </div>

      {/* Stage Label + Message */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className={`text-sm font-semibold ${isCompleted ? 'text-white' : isActive ? 'text-white' : 'text-gray-500'}`}>
            {config.icon} {config.label}
          </span>
        </div>
        <AnimatePresence>
          {event && (
            <motion.p
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="text-xs text-gray-400 mt-0.5 font-mono line-clamp-2"
            >
              {event.message}
            </motion.p>
          )}
        </AnimatePresence>
      </div>

      {/* Timing */}
      {event && (
        <span className="text-[10px] text-gray-600 font-mono flex-shrink-0">
          {new Date(event.timestamp * 1000).toLocaleTimeString()}
        </span>
      )}
    </motion.div>
  )
}

// ─── IngestionPipelinePanel ──────────────────────────────────────────────────

interface IngestionPipelinePanelProps {
  platform: 'bugcrowd' | 'hackerone' | null
  visible: boolean
  onComplete?: (data: any) => void
  onError?: (error: string) => void
  onClose?: () => void
}

export const IngestionPipelinePanel: React.FC<IngestionPipelinePanelProps> = ({
  platform,
  visible,
  onComplete,
  onError,
  onClose,
}) => {
  const [stageEvents, setStageEvents] = useState<Map<PipelineStage, StageEvent>>(new Map())
  const [currentStage, setCurrentStage] = useState<PipelineStage | null>(null)
  const [isError, setIsError] = useState(false)
  const [isDone, setIsDone] = useState(false)
  const cleanupRefs = useRef<(() => void)[]>([])
  const logRef = useRef<HTMLDivElement>(null)

  const stages = platform === 'hackerone' ? H1_STAGES : BUGCROWD_STAGES
  const errorStage: PipelineStage = platform === 'hackerone' ? 'h1_sync_error' : 'ingestion_error'
  const completeStage: PipelineStage = platform === 'hackerone' ? 'h1_sync_complete' : 'ingestion_complete'

  // Reset when panel becomes visible
  useEffect(() => {
    if (visible) {
      setStageEvents(new Map())
      setCurrentStage(null)
      setIsError(false)
      setIsDone(false)
    }
  }, [visible, platform])

  // Subscribe to all pipeline events via websocketManager
  useEffect(() => {
    if (!visible) {
      cleanupRefs.current.forEach((fn) => fn())
      cleanupRefs.current = []
      return
    }

    const handlers: (() => void)[] = []

    ALL_STAGE_EVENTS.forEach((eventType) => {
      const unsub = websocketManager.on(eventType, (data: any) => {
        const event: StageEvent = {
          stage: eventType,
          message: data.message || `${eventType} event received`,
          timestamp: data.timestamp || Date.now() / 1000,
          payload: data,
        }

        setStageEvents((prev) => {
          const next = new Map(prev)
          next.set(eventType, event)
          return next
        })

        setCurrentStage(eventType)

        if (eventType === errorStage) {
          setIsError(true)
          onError?.(data.error || 'Pipeline failed')
        } else if (eventType === completeStage) {
          setIsDone(true)
          onComplete?.(data)
        }

        // Auto-scroll log
        setTimeout(() => {
          logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: 'smooth' })
        }, 50)
      })
      handlers.push(unsub)
    })

    cleanupRefs.current = handlers
    return () => {
      handlers.forEach((fn) => fn())
      cleanupRefs.current = []
    }
  }, [visible, platform, errorStage, completeStage, onComplete, onError])

  if (!visible) return null

  const getStageStatus = (stageId: PipelineStage) => {
    const idx = stages.findIndex((s) => s.id === stageId)
    const currentIdx = stages.findIndex((s) => s.id === currentStage)
    return {
      isActive: stageId === currentStage && !isDone && !isError,
      isCompleted: isDone
        ? idx <= stages.length
        : idx < currentIdx,
      isError: isError && stageId === currentStage,
    }
  }

  const completedCount = Array.from(stageEvents.keys()).filter(
    (k) => stages.find((s) => s.id === k)
  ).length

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.96 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.94 }}
      className="relative bg-background-card/90 border border-white/10 rounded-2xl overflow-hidden"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-white/5">
        <div className="flex items-center gap-3">
          <div className={`w-2 h-2 rounded-full ${isError ? 'bg-red-500' : isDone ? 'bg-green-500' : 'bg-primary animate-pulse'}`} />
          <div>
            <h4 className="text-sm font-bold text-white">
              {platform === 'hackerone' ? 'HackerOne Sync' : 'Bugcrowd Ingestion'} Pipeline
            </h4>
            <p className="text-xs text-gray-500">
              {isDone
                ? `Complete — ${completedCount} stages processed`
                : isError
                ? 'Pipeline error encountered'
                : 'Processing in realtime...'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {/* Progress indicator */}
          <div className="flex gap-1">
            {stages.map((s, i) => {
              const { isCompleted, isActive, isError: stageErr } = getStageStatus(s.id)
              return (
                <div
                  key={s.id}
                  className={`h-1 rounded-full transition-all duration-500 ${
                    stageErr ? 'bg-red-500 w-3' : isCompleted ? 'bg-green-500 w-3' : isActive ? 'bg-primary w-5 animate-pulse' : 'bg-white/10 w-2'
                  }`}
                />
              )
            })}
          </div>
          {onClose && (
            <button
              onClick={onClose}
              className="text-gray-500 hover:text-white transition-colors text-lg leading-none"
            >
              ×
            </button>
          )}
        </div>
      </div>

      {/* Stage list */}
      <div ref={logRef} className="p-4 space-y-1.5 max-h-96 overflow-y-auto">
        {stages.map((config) => {
          const { isActive, isCompleted, isError: stageErr } = getStageStatus(config.id)
          return (
            <StageRow
              key={config.id}
              config={config}
              isActive={isActive}
              isCompleted={isCompleted}
              isError={stageErr}
              event={stageEvents.get(config.id)}
            />
          )
        })}

        {/* Error detail */}
        <AnimatePresence>
          {isError && stageEvents.has(errorStage) && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              className="mt-2 p-3 bg-red-500/10 border border-red-500/30 rounded-xl"
            >
              <p className="text-xs text-red-400 font-mono">
                {stageEvents.get(errorStage)?.message || 'Unknown error'}
              </p>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Success summary */}
        <AnimatePresence>
          {isDone && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-2 p-4 bg-green-500/10 border border-green-500/30 rounded-xl"
            >
              <div className="flex items-center gap-2 mb-1">
                <span className="text-green-400 font-bold text-sm">✅ Pipeline Complete</span>
              </div>
              {stageEvents.has(completeStage) && (
                <p className="text-xs text-green-400/80 font-mono">
                  {stageEvents.get(completeStage)?.message}
                </p>
              )}
              {(() => {
                const completeData = stageEvents.get(completeStage)?.payload
                if (!completeData) return null
                return (
                  <div className="mt-2 grid grid-cols-3 gap-2">
                    {completeData.assets_imported != null && (
                      <div className="text-center">
                        <div className="text-lg font-bold text-white">{completeData.assets_imported}</div>
                        <div className="text-[10px] text-gray-500">Imported</div>
                      </div>
                    )}
                    {completeData.total_recon_targets != null && (
                      <div className="text-center">
                        <div className="text-lg font-bold text-white">{completeData.total_recon_targets}</div>
                        <div className="text-[10px] text-gray-500">Recon Targets</div>
                      </div>
                    )}
                    {completeData.duration_seconds != null && (
                      <div className="text-center">
                        <div className="text-lg font-bold text-white">{Number(completeData.duration_seconds).toFixed(1)}s</div>
                        <div className="text-[10px] text-gray-500">Duration</div>
                      </div>
                    )}
                  </div>
                )
              })()}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  )
}

export default IngestionPipelinePanel
