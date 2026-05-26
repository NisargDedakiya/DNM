import React from 'react'

const toneForSeverity = (severity) => {
  switch ((severity || '').toLowerCase()) {
    case 'critical': return 'border-red-400/20 bg-red-400/10 text-red-100'
    case 'high': return 'border-orange-400/20 bg-orange-400/10 text-orange-100'
    case 'medium': return 'border-amber-400/20 bg-amber-400/10 text-amber-100'
    default: return 'border-emerald-400/20 bg-emerald-400/10 text-emerald-100'
  }
}

const BlastRadiusPanel = ({ blastRadius = null, loading = false }) => {
  const assets = blastRadius?.affected_assets || []

  return (
    <section className="rounded-3xl border border-white/10 bg-white/[0.03] p-5 text-white">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.35em] text-cyan-300">Blast radius</p>
          <h3 className="mt-2 text-lg font-semibold">Impact visualization</h3>
        </div>
        <div className={`rounded-full border px-3 py-1 text-xs font-semibold ${toneForSeverity(blastRadius?.severity || 'info')}`}>
          {loading ? 'Measuring...' : (blastRadius?.severity || 'idle')}
        </div>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <div className="rounded-2xl border border-white/10 bg-slate-950/60 p-4">
          <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">Impact score</div>
          <div className="mt-2 text-3xl font-semibold text-white">{blastRadius?.impact_score ?? 0}</div>
        </div>
        <div className="rounded-2xl border border-white/10 bg-slate-950/60 p-4 md:col-span-2">
          <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">Summary</div>
          <div className="mt-2 text-sm leading-6 text-slate-300">{blastRadius?.summary || 'No blast radius analysis available yet.'}</div>
        </div>
      </div>

      <div className="mt-4 rounded-2xl border border-white/10 bg-slate-950/60 p-4">
        <div className="text-sm font-semibold text-white">Affected assets</div>
        <div className="mt-3 grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
          {assets.length === 0 ? (
            <div className="rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-sm text-slate-400 sm:col-span-2 xl:col-span-3">No affected assets identified.</div>
          ) : (
            assets.map((asset) => (
              <div key={asset} className="rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-sm text-slate-200">{asset}</div>
            ))
          )}
        </div>
      </div>
    </section>
  )
}

export default BlastRadiusPanel