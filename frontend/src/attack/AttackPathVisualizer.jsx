import React, { useMemo } from 'react'

const toneForSeverity = (severity) => {
  switch ((severity || '').toLowerCase()) {
    case 'critical': return 'border-red-400/20 bg-red-400/10 text-red-100'
    case 'high': return 'border-orange-400/20 bg-orange-400/10 text-orange-100'
    case 'medium': return 'border-amber-400/20 bg-amber-400/10 text-amber-100'
    default: return 'border-emerald-400/20 bg-emerald-400/10 text-emerald-100'
  }
}

const AttackPathVisualizer = ({ analysis = null, loading = false, error = '' }) => {
  const paths = analysis?.paths || []

  const stats = useMemo(() => ([
    { label: 'Attack paths', value: paths.length },
    { label: 'Blast score', value: analysis?.blast_radius?.impact_score ?? 0 },
    { label: 'Privilege severity', value: analysis?.privilege_chain?.severity || 'n/a' },
    { label: 'AI verdict', value: analysis?.ai_verdict ? 'ready' : 'pending' },
  ]), [analysis, paths.length])

  return (
    <section className="rounded-[2rem] border border-white/10 bg-slate-950/90 p-6 text-white shadow-[0_24px_90px_rgba(0,0,0,0.34)] backdrop-blur">
      <div className="flex flex-col gap-4 border-b border-white/10 pb-5 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.35em] text-cyan-300">Attack reasoning</p>
          <h2 className="mt-2 text-2xl font-semibold">Advanced attack-path visualization</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-300">
            Org-scoped attack-path reasoning with exploitability propagation, trust-boundary analysis, and blast-radius context.
          </p>
        </div>
        <div className={`rounded-2xl border px-4 py-3 text-sm font-semibold ${toneForSeverity(analysis?.blast_radius?.severity || analysis?.severity || 'info')}`}>
          {loading ? 'Reasoning...' : (analysis?.blast_radius?.severity || analysis?.severity || 'idle')}
        </div>
      </div>

      {error ? <div className="mt-4 rounded-2xl border border-red-400/20 bg-red-400/10 px-4 py-3 text-sm text-red-100">{error}</div> : null}

      <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {stats.map((stat) => (
          <div key={stat.label} className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
            <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">{stat.label}</div>
            <div className="mt-2 text-2xl font-semibold text-white">{stat.value}</div>
          </div>
        ))}
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-2">
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
          <div className="text-sm font-semibold text-white">Graph-aware path chain</div>
          <div className="mt-4 space-y-3">
            {paths.length === 0 ? (
              <div className="rounded-2xl border border-white/10 bg-slate-950/60 p-4 text-sm text-slate-400">No attack paths available yet.</div>
            ) : (
              paths.slice(0, 5).map((path, index) => (
                <div key={`${path.source_asset?.id || index}-${path.target_asset?.id || index}`} className="rounded-2xl border border-white/10 bg-slate-950/60 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div className="text-sm font-medium text-white">{path.source_asset?.hostname || 'Source'} → {path.target_asset?.hostname || 'Target'}</div>
                    <div className={`rounded-full border px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] ${toneForSeverity(path.severity)}`}>{path.severity}</div>
                  </div>
                  <div className="mt-2 text-sm text-slate-300">{path.summary}</div>
                  <div className="mt-2 text-xs text-slate-400">Exploitability {path.exploitability_score ?? 0} · Amplification {path.amplification ?? 0}</div>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
          <div className="text-sm font-semibold text-white">Exploitability indicators</div>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <div className="rounded-2xl border border-white/10 bg-slate-950/60 p-4">
              <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">Blast radius</div>
              <div className="mt-2 text-3xl font-semibold text-white">{analysis?.blast_radius?.impact_score ?? 0}</div>
            </div>
            <div className="rounded-2xl border border-white/10 bg-slate-950/60 p-4">
              <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">Business impact</div>
              <div className="mt-2 text-3xl font-semibold text-white">{analysis?.business_impact?.business_impact_score ?? 0}</div>
            </div>
            <div className="rounded-2xl border border-white/10 bg-slate-950/60 p-4">
              <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">Trust risk</div>
              <div className="mt-2 text-3xl font-semibold text-white">{analysis?.trust_boundary?.boundary_risk ?? 0}</div>
            </div>
            <div className="rounded-2xl border border-white/10 bg-slate-950/60 p-4">
              <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">Privilege severity</div>
              <div className="mt-2 text-3xl font-semibold text-white">{analysis?.privilege_chain?.severity || 'n/a'}</div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

export default AttackPathVisualizer