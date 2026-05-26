import React, { useMemo } from 'react'

const PrivateWorkspacePanel = ({ workspace = null, hunt = null, graph = null }) => {
  const stealthStatus = useMemo(() => workspace?.stealth_enabled || hunt?.visibility === 'restricted', [workspace, hunt])

  return (
    <section className="rounded-3xl border border-white/10 bg-white/[0.03] p-5 text-white">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="text-lg font-semibold">Private workspace</h3>
          <p className="mt-1 text-sm text-slate-400">Confidential investigation controls and stealth workspace isolation.</p>
        </div>
        <div className={`rounded-full px-3 py-1 text-xs font-semibold ${stealthStatus ? 'bg-amber-400/10 text-amber-200' : 'bg-emerald-400/10 text-emerald-200'}`}>
          {stealthStatus ? 'Stealth mode' : 'Public mode'}
        </div>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <div className="rounded-2xl border border-white/10 bg-slate-950/50 p-4">
          <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">Workspace</div>
          <div className="mt-2 text-lg font-semibold">{workspace?.name || 'Unassigned'}</div>
        </div>
        <div className="rounded-2xl border border-white/10 bg-slate-950/50 p-4">
          <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">Hunt visibility</div>
          <div className="mt-2 text-lg font-semibold">{hunt?.visibility || 'restricted'}</div>
        </div>
        <div className="rounded-2xl border border-white/10 bg-slate-950/50 p-4">
          <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">Graph scope</div>
          <div className="mt-2 text-lg font-semibold">{graph?.visibility || 'restricted'}</div>
        </div>
      </div>

      <div className="mt-5 rounded-2xl border border-amber-400/20 bg-amber-400/10 p-4 text-sm text-amber-100">
        Confidential operations stay tenant-scoped, websocket-isolated, and audit-preserving.
      </div>
    </section>
  )
}

export default PrivateWorkspacePanel
