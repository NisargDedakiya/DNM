import React, { useMemo } from 'react'
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, BarChart, Bar, Cell } from 'recharts'

const AIUsageOptimizer = ({ overview = null, ai = null }) => {
  const usageSeries = useMemo(() => {
    const samples = overview?.overview?.ai?.token_usage?.recent || []
    if (samples.length) {
      return samples.slice(-10).map((sample, index) => ({
        name: `R${index + 1}`,
        tokens: Number(sample.total_tokens || 0),
        latency: Number(sample.latency_ms || 0),
      }))
    }
    const tokens = Number(ai?.ai?.token_usage?.total_tokens || 0)
    return [
      { name: 'Current', tokens, latency: Number(overview?.overview?.ai?.latency?.avg_latency_ms || 0) },
      { name: 'Optimized', tokens: Math.max(0, Math.round(tokens * 0.8)), latency: Math.max(0, Math.round((overview?.overview?.ai?.latency?.avg_latency_ms || 0) * 0.75)) },
    ]
  }, [overview, ai])

  const providerData = useMemo(() => {
    const providers = overview?.overview?.ai?.provider_health || []
    return providers.map((provider) => ({
      name: provider.provider,
      latency: Number(provider.avg_latency_ms || 0),
      healthy: provider.healthy,
    }))
  }, [overview])

  const recommendations = ai?.recommendations || [
    'Compress prompts by removing duplicate history and stale context.',
    'Cache repeated AI outputs for identical org-scoped context fingerprints.',
    'Keep model context windows tight around the active investigation scope.',
  ]

  return (
    <section className="rounded-3xl border border-white/10 bg-white/[0.03] p-5">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold text-white">AI usage optimizer</h3>
          <p className="text-sm text-slate-400">Token usage, cache hits, provider latency, and optimization recommendations.</p>
        </div>
        <div className="text-xs text-slate-500">{Math.round((overview?.overview?.ai?.token_usage?.cache_hit_rate || 0) * 100)}% cache hit rate</div>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        <div className="rounded-2xl border border-white/10 bg-slate-950/50 p-4">
          <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">Tokens</div>
          <div className="mt-2 text-2xl font-semibold text-white">{overview?.overview?.ai?.token_usage?.total_tokens || 0}</div>
        </div>
        <div className="rounded-2xl border border-white/10 bg-slate-950/50 p-4">
          <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">Latency</div>
          <div className="mt-2 text-2xl font-semibold text-white">{Math.round(overview?.overview?.ai?.latency?.avg_latency_ms || 0)} ms</div>
        </div>
        <div className="rounded-2xl border border-white/10 bg-slate-950/50 p-4">
          <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">Cache hits</div>
          <div className="mt-2 text-2xl font-semibold text-white">{overview?.overview?.ai?.token_usage?.cache_hits || 0}</div>
        </div>
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-2">
        <div className="rounded-2xl border border-white/10 bg-slate-950/50 p-4">
          <div className="text-sm font-semibold text-white">Token and latency trends</div>
          <div className="mt-4 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={usageSeries}>
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
          <div className="text-sm font-semibold text-white">Provider latency</div>
          <div className="mt-4 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={providerData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
                <XAxis dataKey="name" stroke="rgba(255,255,255,0.4)" />
                <YAxis stroke="rgba(255,255,255,0.4)" />
                <Tooltip contentStyle={{ backgroundColor: '#0b1020', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '12px', color: '#fff' }} />
                <Bar dataKey="latency" radius={[8, 8, 0, 0]}>
                  {providerData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.healthy ? '#22c55e' : '#f59e0b'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="mt-5 rounded-2xl border border-white/10 bg-white/[0.03] p-4">
        <div className="text-sm font-semibold text-white">Optimization recommendations</div>
        <div className="mt-3 space-y-2 text-sm text-slate-300">
          {recommendations.map((item) => (
            <div key={item} className="rounded-xl border border-white/10 bg-black/20 px-3 py-2">{item}</div>
          ))}
        </div>
      </div>
    </section>
  )
}

export default AIUsageOptimizer
