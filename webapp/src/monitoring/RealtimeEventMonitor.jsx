import React, { useEffect, useMemo, useState } from 'react'
import api from '../api/client'
import useRealtimeStore from '../store/useRealtimeStore'

const RealtimeEventMonitor = ({ organizationId, healthSnapshot = null, metricsSnapshot = null }) => {
  const recentEvents = useRealtimeStore((state) => state.recentEvents)
  const [payload, setPayload] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let mounted = true
    const load = async () => {
      if (!organizationId) return
      try {
        const response = await api.get('/monitoring/websocket', { params: { organization_id: organizationId } })
        if (mounted) {
          setPayload(response.data)
          setError('')
        }
      } catch (err) {
        if (mounted) setError(err?.response?.data?.detail || err?.message || 'Failed to load websocket telemetry')
      }
    }

    load()
    const interval = window.setInterval(load, 8000)
    return () => {
      mounted = false
      window.clearInterval(interval)
    }
  }, [organizationId])

  const feed = useMemo(() => {
    const telemetryEvents = payload?.recent_events || metricsSnapshot?.metrics?.recent_events || []
    return [...recentEvents.slice(0, 10), ...telemetryEvents.slice(0, 10)]
      .map((event, index) => ({
        id: `${event?.timestamp || event?.recorded_at || index}-${index}`,
        type: event?.type || event?.event || event?.name || 'event',
        source: event?.organization_id ? 'org' : 'client',
        latency: event?.latency_ms ?? event?.value ?? null,
      }))
      .slice(0, 16)
  }, [recentEvents, payload, metricsSnapshot])

  return (
    <section className="rounded-3xl border border-white/10 bg-white/[0.03] p-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold text-white">Realtime event monitor</h3>
          <p className="text-sm text-slate-400">Redis stream and websocket delivery visibility.</p>
        </div>
        <div className="text-xs text-slate-500">{payload?.websocket?.connection_count || 0} websocket connections · {payload?.websocket?.avg_delivery_latency_ms || 0} ms delivery</div>
      </div>

      {error ? <div className="mt-4 rounded-2xl border border-red-400/20 bg-red-400/10 px-4 py-3 text-sm text-red-100">{error}</div> : null}

      <div className="mt-4 grid gap-3 md:grid-cols-4">
        <div className="rounded-2xl border border-white/10 bg-slate-950/50 p-4">
          <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">Websocket</div>
          <div className="mt-2 text-2xl font-semibold text-white">{payload?.websocket?.healthy ? 'Healthy' : 'Degraded'}</div>
        </div>
        <div className="rounded-2xl border border-white/10 bg-slate-950/50 p-4">
          <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">Reconnects</div>
          <div className="mt-2 text-2xl font-semibold text-white">{payload?.websocket?.reconnects || 0}</div>
        </div>
        <div className="rounded-2xl border border-white/10 bg-slate-950/50 p-4">
          <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">Event stream</div>
          <div className="mt-2 text-2xl font-semibold text-white">{payload?.websocket?.recent_events?.length || healthSnapshot?.metrics?.count || 0}</div>
        </div>
        <div className="rounded-2xl border border-white/10 bg-slate-950/50 p-4">
          <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">Client feed</div>
          <div className="mt-2 text-2xl font-semibold text-white">{recentEvents.length}</div>
        </div>
      </div>

      <div className="mt-5 rounded-2xl border border-white/10 bg-slate-950/50 p-4">
        <div className="flex items-center justify-between gap-3">
          <div className="text-sm font-semibold text-white">Live stream</div>
          <div className="text-xs text-slate-500">Redis + websocket telemetry</div>
        </div>
        <div className="mt-4 max-h-80 space-y-2 overflow-y-auto pr-1">
          {feed.length ? feed.map((event) => (
            <div key={event.id} className="flex items-center justify-between gap-3 rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3 text-sm text-slate-200">
              <div>
                <div className="font-semibold text-white">{event.type}</div>
                <div className="text-xs text-slate-400">source: {event.source}</div>
              </div>
              <div className="text-xs text-slate-400">{event.latency !== null ? `${Math.round(Number(event.latency))} ms` : 'stream'}</div>
            </div>
          )) : (
            <div className="rounded-2xl border border-dashed border-white/10 bg-white/[0.02] p-5 text-sm text-slate-400">
              No realtime events observed yet.
            </div>
          )}
        </div>
      </div>
    </section>
  )
}

export default RealtimeEventMonitor
