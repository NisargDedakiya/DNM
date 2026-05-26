import React, { useMemo } from 'react'

const severityTone = {
  critical: 'border-red-400/20 bg-red-400/10 text-red-100',
  high: 'border-orange-400/20 bg-orange-400/10 text-orange-100',
  medium: 'border-amber-400/20 bg-amber-400/10 text-amber-100',
  low: 'border-emerald-400/20 bg-emerald-400/10 text-emerald-100',
  info: 'border-slate-400/20 bg-slate-400/10 text-slate-100',
}

const ThreatIntelDashboard = ({ summary = null, loading = false, error = '' }) => {
  const metrics = useMemo(() => {
    const summaries = summary?.summaries || []
    return [
      { label: 'Assets analyzed', value: summary?.total_assets ?? 0 },
      { label: 'Threat summaries', value: summaries.length },
      { label: 'Provider hits', value: Object.keys(summary?.provider_exposure?.provider_counts || {}).length },
      { label: 'Malicious hosts', value: summary?.malicious_hosts?.length ?? 0 },
    ]
  }, [summary])

  return (
    <section className="rounded-[2rem] border border-white/10 bg-slate-950/90 p-6 text-white shadow-[0_24px_90px_rgba(0,0,0,0.34)] backdrop-blur">
      <div className="flex flex-col gap-4 border-b border-white/10 pb-5 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.35em] text-cyan-300">Threat intelligence</p>
          <h2 className="mt-2 text-2xl font-semibold">External enrichment and exploitability</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-300">
            Realtime visibility into CVEs, public exposure, GitHub leaks, IP reputation, and ASN correlation.
          </p>
        </div>
        <div className={`rounded-2xl border px-4 py-3 text-sm font-semibold ${severityTone[summary?.severity || 'info']}`}>
          {loading ? 'Enriching...' : (summary?.severity || 'idle')}
        </div>
      </div>

      {error ? <div className="mt-4 rounded-2xl border border-red-400/20 bg-red-400/10 px-4 py-3 text-sm text-red-100">{error}</div> : null}

      <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {metrics.map((metric) => (
          <div key={metric.label} className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
            <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">{metric.label}</div>
            <div className="mt-2 text-3xl font-semibold text-white">{metric.value}</div>
          </div>
        ))}
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-3">
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 xl:col-span-2">
          <div className="flex items-center justify-between gap-3">
            <h3 className="text-lg font-semibold">Threat summary</h3>
            <div className={`rounded-full border px-3 py-1 text-xs font-semibold ${severityTone[summary?.severity || 'info']}`}>{summary?.severity || 'info'}</div>
          </div>
          <p className="mt-3 text-sm leading-6 text-slate-300">{summary?.summary || 'No enrichment has been loaded yet.'}</p>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {(summary?.summaries || []).slice(0, 4).map((item, index) => (
              <div key={`${item.asset_id || index}`} className="rounded-2xl border border-white/10 bg-slate-950/60 p-4">
                <div className="text-xs uppercase tracking-[0.22em] text-slate-400">{item.asset?.hostname || item.asset_id || 'Asset'}</div>
                <div className="mt-2 text-sm text-slate-200">Exploitability {item.exploitability_score ?? item.correlation?.exploitability_score ?? 0}</div>
                <div className="mt-1 text-xs text-slate-400">{item.summary || item.correlation?.summary || 'Correlated external intelligence'}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
          <h3 className="text-lg font-semibold">Priority signals</h3>
          <div className="mt-4 space-y-3">
            {(summary?.malicious_hosts || []).slice(0, 3).map((item, index) => (
              <div key={`${item.ip_address || index}`} className="rounded-2xl border border-white/10 bg-slate-950/60 p-3">
                <div className="text-sm font-medium text-white">{item.ip_address || 'Unknown host'}</div>
                <div className="mt-1 text-xs text-slate-400">{item.severity || 'low'} · reputation {item.reputation_score ?? 0}</div>
              </div>
            ))}
            {(!summary?.malicious_hosts || summary.malicious_hosts.length === 0) ? <div className="text-sm text-slate-400">No high-risk hosts detected.</div> : null}
          </div>
        </div>
      </div>
    </section>
  )
}

export default ThreatIntelDashboard