import React, { useEffect, useMemo, useState } from 'react'
import api from '../api/client'
import useAuthStore from '../stores/authStore'
import useRealtimeStore from '../store/useRealtimeStore'
import WebSocketMetrics from './WebSocketMetrics'
import AIUsageOptimizer from './AIUsageOptimizer'
import GraphPerformancePanel from './GraphPerformancePanel'

const cardTone = (value) => {
  if (value >= 0.85) return 'text-emerald-100 border-emerald-400/20 bg-emerald-400/10'
  if (value >= 0.7) return 'text-cyan-100 border-cyan-400/20 bg-cyan-400/10'
  if (value >= 0.5) return 'text-amber-100 border-amber-400/20 bg-amber-400/10'
  return 'text-red-100 border-red-400/20 bg-red-400/10'
}

const PerformanceDashboard = ({ organizationId: organizationIdProp = null }) => {
  const currentUser = useAuthStore((state) => state.user)
  const isConnected = useRealtimeStore((state) => state.isConnected)
  const recentEvents = useRealtimeStore((state) => state.recentEvents)
  const organizationId = organizationIdProp || currentUser?.organization_id || ''

  const [overview, setOverview] = useState(null)
  const [websocket, setWebsocket] = useState(null)
  const [ai, setAi] = useState(null)
  const [queues, setQueues] = useState(null)
  const [graph, setGraph] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let mounted = true

    const load = async () => {
      if (!organizationId) return
      setLoading(true)
      try {
        const [overviewResponse, websocketResponse, aiResponse, queuesResponse, graphResponse] = await Promise.all([
          api.get('/performance/overview', { params: { organization_id: organizationId } }),
          api.get('/performance/websocket', { params: { organization_id: organizationId } }),
          api.get('/performance/ai', { params: { organization_id: organizationId } }),
          api.get('/performance/queues', { params: { organization_id: organizationId } }),
          api.get('/performance/graph', { params: { organization_id: organizationId } }),
        ])
        if (mounted) {
          setOverview(overviewResponse.data)
          setWebsocket(websocketResponse.data)
          setAi(aiResponse.data)
          setQueues(queuesResponse.data)
          setGraph(graphResponse.data)
          setError('')
        }
      } catch (err) {
        if (mounted) setError(err?.response?.data?.detail || err?.message || 'Failed to load performance data')
      } finally {
        if (mounted) setLoading(false)
      }
    }

    load()
    const interval = window.setInterval(load, 15000)
    return () => {
      mounted = false
      window.clearInterval(interval)
    }
  }, [organizationId])

  const summaryCards = useMemo(() => {
    const healthScore = Number(overview?.overview?.health_score || overview?.health_score || 0)
    const websocketConnections = Number(websocket?.websocket?.connection_count || overview?.overview?.websocket?.connection_count || 0)
    const aiTokens = Number(overview?.overview?.ai?.token_usage?.total_tokens || 0)
    const queueDepth = Number(queues?.queue_depth || overview?.overview?.redis?.queue_depth || 0)
    return [
      { label: 'Platform health', value: `${Math.round(healthScore * 100)}%`, tone: cardTone(healthScore) },
      { label: 'WebSocket connections', value: websocketConnections, tone: 'text-cyan-100 border-cyan-400/20 bg-cyan-400/10' },
      { label: 'AI tokens', value: aiTokens, tone: 'text-fuchsia-100 border-fuchsia-400/20 bg-fuchsia-400/10' },
      { label: 'Queue depth', value: queueDepth, tone: 'text-amber-100 border-amber-400/20 bg-amber-400/10' },
    ]
  }, [overview, websocket, ai, queues])

  return (
    <section className="rounded-[2rem] border border-white/10 bg-slate-950/80 p-6 shadow-[0_24px_90px_rgba(0,0,0,0.34)] backdrop-blur">
      <div className="flex flex-col gap-4 border-b border-white/10 pb-5 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.35em] text-cyan-300">Performance</p>
          <h2 className="mt-2 text-2xl font-semibold text-white">Platform performance dashboard</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-300">
            Low-latency visibility into websocket throughput, AI efficiency, queue pressure, and graph rendering cost.
          </p>
        </div>
        <div className={`rounded-2xl border px-4 py-3 text-sm font-semibold ${isConnected ? 'border-emerald-400/20 bg-emerald-400/10 text-emerald-100' : 'border-amber-400/20 bg-amber-400/10 text-amber-100'}`}>
          {loading ? 'Refreshing...' : (isConnected ? 'Realtime sync active' : 'Realtime sync unavailable')}
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
          <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">Queue pressure</div>
          <div className="mt-2 text-3xl font-semibold text-white">{Math.round((queues?.queue_pressure?.backlog_pressure || 0) * 100)}%</div>
          <div className="mt-2 text-sm text-slate-300">{queues?.queue_pressure?.recommended_action || 'steady_state'}</div>
        </div>
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
          <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">WebSocket latency</div>
          <div className="mt-2 text-3xl font-semibold text-white">{Math.round(websocket?.websocket?.avg_delivery_latency_ms || 0)} ms</div>
          <div className="mt-2 text-sm text-slate-300">{websocket?.websocket?.reconnects || 0} reconnects observed</div>
        </div>
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
          <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">AI cache hit rate</div>
          <div className="mt-2 text-3xl font-semibold text-white">{Math.round((overview?.overview?.ai?.token_usage?.cache_hit_rate || 0) * 100)}%</div>
          <div className="mt-2 text-sm text-slate-300">Provider efficiency under active optimization</div>
        </div>
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
          <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">Recent events</div>
          <div className="mt-2 text-3xl font-semibold text-white">{recentEvents.length}</div>
          <div className="mt-2 text-sm text-slate-300">Realtime event stream visibility</div>
        </div>
      </div>

      <div className="mt-6 grid gap-6 2xl:grid-cols-2">
        <WebSocketMetrics overview={overview} websocket={websocket} queues={queues} />
        <AIUsageOptimizer overview={overview} ai={ai} />
      </div>

      <div className="mt-6">
        <GraphPerformancePanel overview={overview} graph={graph} queues={queues} />
      </div>
    </section>
  )
}

export default PerformanceDashboard
