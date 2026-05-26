import React from 'react'

const toneForSeverity = (severity) => {
  switch ((severity || '').toLowerCase()) {
    case 'critical': return 'border-red-400/20 bg-red-400/10 text-red-100'
    case 'high': return 'border-orange-400/20 bg-orange-400/10 text-orange-100'
    case 'medium': return 'border-amber-400/20 bg-amber-400/10 text-amber-100'
    default: return 'border-emerald-400/20 bg-emerald-400/10 text-emerald-100'
  }
}

const CVECorrelationPanel = ({ cves = [], assetName = '', loading = false }) => {
  return (
    <section className="rounded-3xl border border-white/10 bg-white/[0.03] p-5 text-white">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.35em] text-cyan-300">CVE correlation</p>
          <h3 className="mt-2 text-lg font-semibold">{assetName || 'Asset'} vulnerability mapping</h3>
        </div>
        <div className="text-xs text-slate-400">{loading ? 'Updating...' : `${cves.length} matches`}</div>
      </div>

      <div className="mt-4 space-y-3">
        {cves.length === 0 ? (
          <div className="rounded-2xl border border-white/10 bg-slate-950/60 p-4 text-sm text-slate-400">No CVE matches available yet.</div>
        ) : (
          cves.map((item) => (
            <div key={item.cve_id} className="rounded-2xl border border-white/10 bg-slate-950/60 p-4">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="text-sm font-semibold text-white">{item.cve_id}</div>
                  <div className="mt-1 text-xs text-slate-400">{item.title}</div>
                </div>
                <div className={`rounded-full border px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] ${toneForSeverity(item.severity)}`}>{item.severity || 'info'}</div>
              </div>
              <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
                <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3">
                  <div className="text-[11px] uppercase tracking-[0.2em] text-slate-400">CVSS</div>
                  <div className="mt-1 text-lg font-semibold text-white">{item.cvss_score ?? 0}</div>
                </div>
                <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3">
                  <div className="text-[11px] uppercase tracking-[0.2em] text-slate-400">Exploitability</div>
                  <div className="mt-1 text-lg font-semibold text-white">{item.exploitability ?? 0}</div>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </section>
  )
}

export default CVECorrelationPanel