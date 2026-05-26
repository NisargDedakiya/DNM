import React from 'react'

const LateralMovementView = ({ movement = null, loading = false }) => {
  const pivots = movement?.pivot_paths || []

  return (
    <section className="rounded-3xl border border-white/10 bg-slate-950/80 p-5 text-white">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.35em] text-cyan-300">Lateral movement</p>
          <h3 className="mt-2 text-lg font-semibold">Pivot-path simulation</h3>
        </div>
        <div className="text-xs text-slate-400">{loading ? 'Simulating...' : `${pivots.length} pivots`}</div>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
          <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">Movement score</div>
          <div className="mt-2 text-3xl font-semibold text-white">{movement?.movement_score ?? 0}</div>
        </div>
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
          <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">Severity</div>
          <div className="mt-2 text-3xl font-semibold text-white">{movement?.severity || 'idle'}</div>
        </div>
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 md:col-span-2 xl:col-span-1">
          <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">Summary</div>
          <div className="mt-2 text-sm leading-6 text-slate-300">{movement?.summary || 'No lateral movement simulation available yet.'}</div>
        </div>
      </div>

      <div className="mt-4 space-y-3">
        {pivots.length === 0 ? (
          <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 text-sm text-slate-400">No pivot opportunities identified.</div>
        ) : pivots.map((pivot) => (
          <div key={pivot.asset_id || pivot.hostname} className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
            <div className="flex items-center justify-between gap-3">
              <div className="text-sm font-medium text-white">{pivot.hostname || pivot.asset_id}</div>
              <div className="text-xs uppercase tracking-[0.2em] text-slate-400">pivot {pivot.pivot_score ?? 0}</div>
            </div>
            <div className="mt-2 text-sm text-slate-300">{pivot.reason}</div>
          </div>
        ))}
      </div>
    </section>
  )
}

export default LateralMovementView