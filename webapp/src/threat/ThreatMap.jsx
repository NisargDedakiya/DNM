import React from 'react'

const ThreatMap = ({ asnData = [], loading = false }) => {
  return (
    <section className="rounded-3xl border border-white/10 bg-white/[0.03] p-5 text-white">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.35em] text-cyan-300">Infrastructure map</p>
          <h3 className="mt-2 text-lg font-semibold">ASN ownership and exposure relationships</h3>
        </div>
        <div className="text-xs text-slate-400">{loading ? 'Resolving...' : `${asnData.length} nodes`}</div>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {asnData.length === 0 ? (
          <div className="rounded-2xl border border-white/10 bg-slate-950/60 p-4 text-sm text-slate-400 md:col-span-2 xl:col-span-3">No ASN intelligence available.</div>
        ) : (
          asnData.map((item, index) => (
            <div key={item.asn || index} className="rounded-2xl border border-white/10 bg-slate-950/60 p-4">
              <div className="text-sm font-semibold text-white">{item.owner || item.provider || 'Unknown provider'}</div>
              <div className="mt-1 text-xs text-slate-400">ASN {item.asn || 'n/a'} · {item.country || 'unknown region'}</div>
              <div className="mt-3 text-xs text-slate-300">Ownership: {item.ownership_type || 'enterprise'}</div>
            </div>
          ))
        )}
      </div>
    </section>
  )
}

export default ThreatMap