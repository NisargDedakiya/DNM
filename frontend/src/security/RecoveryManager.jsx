import React from 'react'

const RecoveryManager = ({ recovery = null, loading = false }) => {
  return (
    <section className="rounded-3xl border border-white/10 bg-white/[0.03] p-5 text-white">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.35em] text-cyan-300">Recovery</p>
          <h3 className="mt-2 text-lg font-semibold">Backup and disaster recovery</h3>
        </div>
        <div className="text-xs text-slate-400">{loading ? 'Updating...' : (recovery?.status || 'idle')}</div>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <div className="rounded-2xl border border-white/10 bg-slate-950/60 p-4">
          <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">Snapshots</div>
          <div className="mt-2 text-3xl font-semibold text-white">{recovery?.snapshot_count ?? 0}</div>
        </div>
        <div className="rounded-2xl border border-white/10 bg-slate-950/60 p-4 md:col-span-2">
          <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">Summary</div>
          <div className="mt-2 text-sm leading-6 text-slate-300">{recovery?.summary || 'No recovery workflow has been triggered.'}</div>
        </div>
      </div>

      <div className="mt-4 rounded-2xl border border-white/10 bg-slate-950/60 p-4 text-sm text-slate-300">
        Recovery workflows remain org-scoped and integrity-checked before restoration.
      </div>
    </section>
  )
}

export default RecoveryManager