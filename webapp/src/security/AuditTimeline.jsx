import React from 'react'

const AuditTimeline = ({ entries = [], loading = false }) => {
  return (
    <section className="rounded-3xl border border-white/10 bg-white/[0.03] p-5 text-white">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.35em] text-cyan-300">Audit trail</p>
          <h3 className="mt-2 text-lg font-semibold">Immutable forensic timeline</h3>
        </div>
        <div className="text-xs text-slate-400">{loading ? 'Loading...' : `${entries.length} records`}</div>
      </div>

      <div className="mt-4 space-y-3">
        {entries.length === 0 ? (
          <div className="rounded-2xl border border-white/10 bg-slate-950/60 p-4 text-sm text-slate-400">No audit entries available yet.</div>
        ) : entries.map((entry) => (
          <div key={entry.id || entry.integrity_hash} className="rounded-2xl border border-white/10 bg-slate-950/60 p-4">
            <div className="flex items-center justify-between gap-3">
              <div className="text-sm font-medium text-white">{entry.actor || 'system'}</div>
              <div className="text-xs uppercase tracking-[0.2em] text-slate-400">{entry.created_at || 'recent'}</div>
            </div>
            <div className="mt-2 text-sm text-slate-300">{entry.action || 'audit_action'}</div>
            <div className="mt-2 text-xs text-slate-400 break-all">{entry.integrity_hash || 'no_hash'}</div>
          </div>
        ))}
      </div>
    </section>
  )
}

export default AuditTimeline