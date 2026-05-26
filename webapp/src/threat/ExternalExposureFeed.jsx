import React from 'react'

const ExternalExposureFeed = ({ exposures = [], loading = false }) => {
  return (
    <section className="rounded-3xl border border-white/10 bg-slate-950/80 p-5 text-white">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.35em] text-cyan-300">External feed</p>
          <h3 className="mt-2 text-lg font-semibold">Realtime enrichment updates</h3>
        </div>
        <div className="text-xs text-slate-400">{loading ? 'Syncing...' : `${exposures.length} events`}</div>
      </div>

      <div className="mt-4 space-y-3">
        {exposures.length === 0 ? (
          <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 text-sm text-slate-400">No external exposure events yet.</div>
        ) : (
          exposures.map((item, index) => (
            <div key={item.id || index} className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
              <div className="flex items-center justify-between gap-3">
                <div className="text-sm font-semibold text-white">{item.asset?.hostname || item.asset || 'Unknown asset'}</div>
                <div className="text-xs uppercase tracking-[0.2em] text-slate-400">{item.source || 'feed'}</div>
              </div>
              <div className="mt-2 text-sm text-slate-300">{item.summary || item.exposure_type || 'Exposure signal detected'}</div>
              <div className="mt-2 text-xs text-slate-400">Severity: {item.severity || 'info'} · Type: {item.exposure_type || item.type || 'unknown'}</div>
            </div>
          ))
        )}
      </div>
    </section>
  )
}

export default ExternalExposureFeed