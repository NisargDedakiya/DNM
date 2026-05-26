import React, { useMemo } from 'react'

const severityTone = (severity) => {
  switch ((severity || '').toLowerCase()) {
    case 'critical': return 'border-red-400/20 bg-red-400/10 text-red-100'
    case 'high': return 'border-orange-400/20 bg-orange-400/10 text-orange-100'
    case 'medium': return 'border-amber-400/20 bg-amber-400/10 text-amber-100'
    default: return 'border-emerald-400/20 bg-emerald-400/10 text-emerald-100'
  }
}

const SecurityOperationsDashboard = ({ summary = null, loading = false, error = '' }) => {
  const cards = useMemo(() => ([
    { label: 'Security events', value: summary?.integrity?.record_count ?? 0 },
    { label: 'Audit entries', value: summary?.audit_entries ?? summary?.integrity?.record_count ?? 0 },
    { label: 'Recovery snapshots', value: summary?.recovery?.snapshot_count ?? 0 },
    { label: 'Rate budget', value: summary?.rate_limit?.request_budget ?? 0 },
  ]), [summary])

  return (
    <section className="rounded-[2rem] border border-white/10 bg-slate-950/90 p-6 text-white shadow-[0_24px_90px_rgba(0,0,0,0.34)] backdrop-blur">
      <div className="flex flex-col gap-4 border-b border-white/10 pb-5 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.35em] text-cyan-300">Security operations</p>
          <h2 className="mt-2 text-2xl font-semibold">Production hardening dashboard</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-300">
            Realtime visibility into sandbox execution, abuse prevention, audit integrity, and recovery readiness.
          </p>
        </div>
        <div className={`rounded-2xl border px-4 py-3 text-sm font-semibold ${severityTone(summary?.integrity?.valid === false ? 'critical' : 'low')}`}>
          {loading ? 'Refreshing...' : (summary?.integrity?.valid === false ? 'Audit drift' : 'Hardened')}
        </div>
      </div>

      {error ? <div className="mt-4 rounded-2xl border border-red-400/20 bg-red-400/10 px-4 py-3 text-sm text-red-100">{error}</div> : null}

      <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {cards.map((card) => (
          <div key={card.label} className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
            <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">{card.label}</div>
            <div className="mt-2 text-3xl font-semibold text-white">{card.value}</div>
          </div>
        ))}
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-2">
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
          <div className="text-sm font-semibold text-white">Hardening status</div>
          <div className="mt-3 space-y-3 text-sm text-slate-300">
            <div>Audit integrity: {summary?.integrity?.valid ? 'valid' : 'check required'}</div>
            <div>Throttle budget: {summary?.rate_limit?.request_budget ?? 0} requests / minute</div>
            <div>Recovery state: {summary?.recovery?.snapshot_count ?? 0} snapshots available</div>
            <div>Abuse score: {summary?.abuse?.abuse_score ?? 0}</div>
          </div>
        </div>

        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
          <div className="text-sm font-semibold text-white">Operational summary</div>
          <p className="mt-3 text-sm leading-6 text-slate-300">{summary?.summary || 'No security summary available yet.'}</p>
          <div className="mt-4 rounded-2xl border border-white/10 bg-slate-950/60 p-4 text-xs text-slate-400">
            Secure execution remains org-scoped, rate-limited, sandboxed, and auditable.
          </div>
        </div>
      </div>
    </section>
  )
}

export default SecurityOperationsDashboard