import React, { useMemo } from 'react'
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, AreaChart, Area } from 'recharts'

const WebSocketMetrics = ({ overview = null, websocket = null, queues = null }) => {
  const samples = useMemo(() => {
    const events = overview?.overview?.metrics?.recent_events || []
    const latencySamples = events.filter((event) => String(event.name || '').includes('websocket'))
    if (latencySamples.length) {
      return latencySamples.slice(-12).map((sample, index) => ({
        name: `E${index + 1}`,
        latency: Number(sample.value || 0),
      }))
    }
    const scalarLatency = Number(websocket?.websocket?.avg_delivery_latency_ms || 0)
    return [
      { name: 'Baseline', latency: scalarLatency },
      { name: 'Optimized', latency: Math.max(0, scalarLatency * 0.85) },
      { name: 'Target', latency: Math.max(0, scalarLatency * 0.65) },
    ]
  }, [overview, websocket])

  const throughputSeries = useMemo(() => {
    const connectionCount = Number(websocket?.websocket?.connection_count || 0)
    const queueDepth = Number(queues?.queue_depth || 0)
    return [
      { name: 'Connections', value: connectionCount },
      { name: 'Queue depth', value: queueDepth },
      { name: 'Reconnects', value: Number(websocket?.websocket?.reconnects || 0) },
    ]
  }, [websocket, queues])

  const recommendations = [
    'Batch websocket updates before fan-out to reduce event floods.',
    'Compress duplicate heartbeat and typing events at the edge.',
    'Escalate reconnect storms to slow-path delivery.',
  ]

  return (
    <section className="rounded-3xl border border-white/10 bg-white/[0.03] p-5">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold text-white">WebSocket metrics</h3>
          <p className="text-sm text-slate-400">Latency charts, reconnect tracking, and throughput visibility.</p>
        </div>
        <div className="text-xs text-slate-500">{websocket?.websocket?.healthy ? 'healthy' : 'degraded'}</div>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        <div className="rounded-2xl border border-white/10 bg-slate-950/50 p-4">
          <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">Latency</div>
          <div className="mt-2 text-2xl font-semibold text-white">{Math.round(websocket?.websocket?.avg_delivery_latency_ms || 0)} ms</div>
        </div>
        <div className="rounded-2xl border border-white/10 bg-slate-950/50 p-4">
          <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">Reconnects</div>
          <div className="mt-2 text-2xl font-semibold text-white">{websocket?.websocket?.reconnects || 0}</div>
        </div>
        <div className="rounded-2xl border border-white/10 bg-slate-950/50 p-4">
          <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">Connections</div>
          <div className="mt-2 text-2xl font-semibold text-white">{websocket?.websocket?.connection_count || 0}</div>
        </div>
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-2">
        <div className="rounded-2xl border border-white/10 bg-slate-950/50 p-4">
          <div className="text-sm font-semibold text-white">Latency trend</div>
          <div className="mt-4 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={samples}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
                <XAxis dataKey="name" stroke="rgba(255,255,255,0.4)" />
                <YAxis stroke="rgba(255,255,255,0.4)" />
                <Tooltip contentStyle={{ backgroundColor: '#0b1020', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '12px', color: '#fff' }} />
                <Line type="monotone" dataKey="latency" stroke="#22d3ee" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-2xl border border-white/10 bg-slate-950/50 p-4">
          <div className="text-sm font-semibold text-white">Throughput visibility</div>
          <div className="mt-4 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={throughputSeries}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
                <XAxis dataKey="name" stroke="rgba(255,255,255,0.4)" />
                <YAxis stroke="rgba(255,255,255,0.4)" />
                <Tooltip contentStyle={{ backgroundColor: '#0b1020', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '12px', color: '#fff' }} />
                <Area type="monotone" dataKey="value" stroke="#a855f7" fill="rgba(168,85,247,0.18)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="mt-5 rounded-2xl border border-white/10 bg-white/[0.03] p-4">
        <div className="text-sm font-semibold text-white">Optimization guidance</div>
        <div className="mt-3 space-y-2 text-sm text-slate-300">
          {recommendations.map((item) => (
            <div key={item} className="rounded-xl border border-white/10 bg-black/20 px-3 py-2">{item}</div>
          ))}
        </div>
      </div>
    </section>
  )
}

export default WebSocketMetrics
