import React from 'react'

const RateLimitMonitor = ({ rateLimit = null, loading = false }) => {
  const used = rateLimit?.requests_used ?? 0
  const budget = rateLimit?.request_budget ?? 0
  const percent = budget > 0 ? Math.min(100, Math.round((used / budget) * 100)) : 0

  return (
    <section className="rounded-3xl border border-white/10 bg-slate-950/80 p-5 text-white">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.35em] text-cyan-300">Rate limits</p>
          <h3 className="mt-2 text-lg font-semibold">Org usage and throttle budget</h3>
        </div>
        <div className="text-xs text-slate-400">{loading ? 'Checking...' : `${percent}% used`}</div>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
          <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">Budget</div>
          <div className="mt-2 text-3xl font-semibold text-white">{budget}</div>
        </div>
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
          <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">Used</div>
          <div className="mt-2 text-3xl font-semibold text-white">{used}</div>
        </div>
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
          <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">Status</div>
          <div className="mt-2 text-3xl font-semibold text-white">{rateLimit?.allowed ? 'allowed' : 'throttled'}</div>
        </div>
      </div>

      <div className="mt-4 h-3 overflow-hidden rounded-full bg-white/10">
        <div className={`h-full rounded-full ${percent >= 80 ? 'bg-red-400' : percent >= 60 ? 'bg-amber-400' : 'bg-emerald-400'}`} style={{ width: `${percent}%` }} />
      </div>
      <div className="mt-3 text-sm text-slate-300">{rateLimit?.throttle_reason || 'No throttle pressure detected.'}</div>
    </section>
  )
}

export default RateLimitMonitor