import React, { useEffect, useMemo, useState } from 'react'
import api from '../api/client'
import useAuthStore from '../state/auth'
import useRealtimeStore from '../realtime/realtimeStore'
import WorkerGrid from './WorkerGrid'
import AIMetricsPanel from './AIMetricsPanel'
import RealtimeEventMonitor from './RealtimeEventMonitor'

const toneForScore = (score) => {
  if (score >= 0.85) return 'text-emerald-300 bg-emerald-400/10 border-emerald-400/20'
  if (score >= 0.7) return 'text-cyan-300 bg-cyan-400/10 border-cyan-400/20'
  if (score >= 0.5) return 'text-amber-300 bg-amber-400/10 border-amber-400/20'
  return 'text-red-300 bg-red-400/10 border-red-400/20'
}

const SystemHealthDashboard = ({ organizationId: organizationIdProp = null }) => {
  const { user: currentUser, activeOrgId } = useAuthStore()
  const isConnected = useRealtimeStore((state) => state.isConnected)
  const recentEvents = useRealtimeStore((state) => state.recentEvents)
  const organizationId = organizationIdProp || activeOrgId || ''

  const [health, setHealth] = useState(null)
  const [metrics, setMetrics] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const loadHealth = async () => {
    if (!organizationId) return
    setLoading(true)
    try {
      const [healthResponse, metricsResponse] = await Promise.all([
        api.get('/monitoring/health', { params: { organization_id: organizationId } }),
        api.get('/monitoring/metrics', { params: { organization_id: organizationId } }),
      ])
      setHealth(healthResponse.data)
      setMetrics(metricsResponse.data)
      setError('')
    } catch (err) {
      setError(err?.response?.data?.detail || err?.message || 'Failed to load monitoring data')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadHealth()
    const interval = window.setInterval(loadHealth, 15000)
    return () => window.clearInterval(interval)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [organizationId])

  const system = health?.system?.metrics || health?.system || {}
  const redis = health?.redis || {}
  const websocket = health?.websocket || {}
  const healthScore = health?.health_score ?? 0

  const summaryCards = useMemo(() => ([
    { label: 'Platform health', value: `${Math.round((healthScore || 0) * 100)}%`, tone: toneForScore(healthScore) },
    { label: 'Redis queue depth', value: redis?.queue_depth ?? 0, tone: 'text-cyan-200 bg-cyan-400/10 border-cyan-400/20' },
    { label: 'Websocket connections', value: websocket?.connection_count ?? 0, tone: 'text-fuchsia-200 bg-fuchsia-400/10 border-fuchsia-400/20' },
    { label: 'Recent events', value: recentEvents.length, tone: 'text-amber-200 bg-amber-400/10 border-amber-400/20' },
  ]), [healthScore, redis?.queue_depth, websocket?.connection_count, recentEvents.length])

  return (
    <section className="rounded-[2rem] border border-white/10 bg-slate-950/80 p-6 shadow-[0_24px_90px_rgba(0,0,0,0.34)] backdrop-blur">
      <div className="flex flex-col gap-4 border-b border-white/10 pb-5 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.35em] text-fuchsia-300">Observability</p>
          <h2 className="mt-2 text-2xl font-semibold text-white">System health dashboard</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-300">
            Realtime visibility into system pressure, Redis health, websocket delivery, worker load, and AI performance.
          </p>
        </div>
        <div className={`rounded-2xl border px-4 py-3 text-sm font-semibold ${health?.status === 'healthy' ? 'border-emerald-400/20 bg-emerald-400/10 text-emerald-100' : 'border-amber-400/20 bg-amber-400/10 text-amber-100'}`}>
          {loading ? 'Refreshing...' : (health?.status || 'unknown')}
        </div>
      </div>

      {error ? (
        <div className="mt-4 rounded-2xl border border-red-400/20 bg-red-400/10 px-4 py-3 text-sm text-red-100">{error}</div>
      ) : null}

      <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {summaryCards.map((card) => (
          <div key={card.label} className={`rounded-2xl border p-4 ${card.tone}`}>
            <div className="text-[11px] font-semibold uppercase tracking-[0.24em] opacity-80">{card.label}</div>
            <div className="mt-2 text-2xl font-semibold text-white">{card.value}</div>
          </div>
        ))}
      </div>

      <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
          <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">System pressure</div>
          <div className="mt-2 text-3xl font-semibold text-white">{Math.round((system.pressure_score || health?.system?.pressure_score || 0) * 100)}%</div>
          <div className="mt-2 text-sm text-slate-300">CPU {system.cpu_percent ?? 0}% · Memory {system.memory_percent ?? 0}% · Disk {system.disk_percent ?? 0}%</div>
        </div>
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
          <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">Redis health</div>
          <div className="mt-2 text-3xl font-semibold text-white">{redis.healthy ? 'OK' : 'Degraded'}</div>
          <div className="mt-2 text-sm text-slate-300">Queue depth {redis.queue_depth ?? 0} · Stream {redis.event_stream_length ?? 0}</div>
        </div>
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
          <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">WebSocket health</div>
          <div className="mt-2 text-3xl font-semibold text-white">{isConnected ? 'Connected' : 'Offline'}</div>
          <div className="mt-2 text-sm text-slate-300">{websocket.connection_count ?? 0} org connections · {websocket.avg_delivery_latency_ms ?? 0} ms delivery</div>
        </div>
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
          <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">Platform status</div>
          <div className="mt-2 text-3xl font-semibold text-white">{health?.status || 'unknown'}</div>
          <div className="mt-2 text-sm text-slate-300">{health?.worker_bottlenecks?.length || 0} worker bottlenecks · {health?.websocket_issues?.length || 0} websocket issues</div>
        </div>
      </div>

      <div className="mt-6 grid gap-6 2xl:grid-cols-2">
        <WorkerGrid organizationId={organizationId} healthSnapshot={health} />
        <AIMetricsPanel organizationId={organizationId} metricsSnapshot={metrics} />
      </div>

      <div className="mt-6">
        <RealtimeEventMonitor organizationId={organizationId} healthSnapshot={health} metricsSnapshot={metrics} />
      </div>
    </section>
  )
}

export default SystemHealthDashboard
