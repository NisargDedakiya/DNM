import React, { useEffect, useMemo, useState } from 'react'
import api from '../api/client'
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, BarChart, Bar, Cell } from 'recharts'

const providerTone = (healthy) => (healthy ? 'text-emerald-100 border-emerald-400/20 bg-emerald-400/10' : 'text-red-100 border-red-400/20 bg-red-400/10')

const AIMetricsPanel = ({ organizationId, metricsSnapshot = null }) => {
  const [payload, setPayload] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let mounted = true
    const load = async () => {
      if (!organizationId) return
      try {
        const response = await api.get('/monitoring/ai', { params: { organization_id: organizationId } })
        if (mounted) {
          setPayload(response.data)
          setError('')
        }
      } catch (err) {
        if (mounted) setError(err?.response?.data?.detail || err?.message || 'Failed to load AI metrics')
      }
    }

    load()
    const interval = window.setInterval(load, 15000)
    return () => {
      mounted = false
      window.clearInterval(interval)
    }
  }, [organizationId])

  const tokenSeries = useMemo(() => {
    const source = payload?.token_usage?.recent || metricsSnapshot?.metrics?.recent_events || []
    return source.slice(-8).map((item, index) => ({
      name: `S${index + 1}`,
      tokens: Number(item.total_tokens || item.value || 0),
      latency: Number(item.latency_ms || 0),
    }))
  }, [payload, metricsSnapshot])

  const providerHealth = payload?.provider_health || []

  return (
    <section className="rounded-3xl border border-white/10 bg-white/[0.03] p-5">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold text-white">AI metrics</h3>
          <p className="text-sm text-slate-400">Token usage, latency, and provider stability.</p>
        </div>
        <div className="text-xs text-slate-500">{payload?.token_usage?.cache_hit_rate ? `${Math.round(payload.token_usage.cache_hit_rate * 100)}% cache hit` : 'cache unknown'}</div>
      </div>

      {error ? <div className="mt-4 rounded-2xl border border-red-400/20 bg-red-400/10 px-4 py-3 text-sm text-red-100">{error}</div> : null}

      <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-2xl border border-white/10 bg-slate-950/50 p-4">
          <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">Tokens</div>
          <div className="mt-2 text-2xl font-semibold text-white">{payload?.token_usage?.total_tokens || 0}</div>
        </div>
        <div className="rounded-2xl border border-white/10 bg-slate-950/50 p-4">
          <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">Requests</div>
          <div className="mt-2 text-2xl font-semibold text-white">{payload?.latency?.count || 0}</div>
        </div>
        <div className="rounded-2xl border border-white/10 bg-slate-950/50 p-4">
          <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">Latency</div>
          <div className="mt-2 text-2xl font-semibold text-white">{Math.round(payload?.latency?.avg_latency_ms || 0)} ms</div>
        </div>
        <div className="rounded-2xl border border-white/10 bg-slate-950/50 p-4">
          <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">Cache hits</div>
          <div className="mt-2 text-2xl font-semibold text-white">{payload?.token_usage?.cache_hits || 0}</div>
        </div>
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-2">
        <div className="rounded-2xl border border-white/10 bg-slate-950/50 p-4">
          <div className="text-sm font-semibold text-white">Token and latency trend</div>
          <div className="mt-4 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={tokenSeries}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
                <XAxis dataKey="name" stroke="rgba(255,255,255,0.4)" />
                <YAxis stroke="rgba(255,255,255,0.4)" />
                <Tooltip contentStyle={{ backgroundColor: '#0b1020', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '12px', color: '#fff' }} />
                <Line type="monotone" dataKey="tokens" stroke="#22d3ee" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="latency" stroke="#f472b6" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-2xl border border-white/10 bg-slate-950/50 p-4">
          <div className="text-sm font-semibold text-white">Provider health</div>
          <div className="mt-4 space-y-3">
            {providerHealth.length ? providerHealth.map((provider) => (
              <div key={provider.provider} className={`rounded-2xl border p-4 ${providerTone(provider.healthy)}`}>
                <div className="flex items-center justify-between gap-2">
                  <div>
                    <div className="text-sm font-semibold text-white">{provider.provider}</div>
                    <div className="text-xs opacity-80">{Math.round(provider.avg_latency_ms || 0)} ms avg latency</div>
                  </div>
                  <div className="text-xs font-semibold uppercase tracking-[0.24em] opacity-80">{provider.healthy ? 'healthy' : 'degraded'}</div>
                </div>
                <div className="mt-3 text-xs opacity-80">Failure rate {Math.round((provider.failure_rate || 0) * 100)}%</div>
              </div>
            )) : (
              <div className="rounded-2xl border border-dashed border-white/10 bg-white/[0.02] p-5 text-sm text-slate-400">
                No AI telemetry yet.
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  )
}

export default AIMetricsPanel
