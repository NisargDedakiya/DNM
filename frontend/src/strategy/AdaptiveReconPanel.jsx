import React from 'react';

export default function AdaptiveReconPanel({ followUps = [], evolution = {}, signals = [] }) {
  return (
    <div className="rounded-3xl border border-white/10 bg-slate-950/90 p-6 text-slate-100 shadow-2xl shadow-cyan-950/20">
      <div className="flex items-end justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.35em] text-cyan-300/80">Adaptive Recon</p>
          <h3 className="text-xl font-semibold text-white">Evolving scan logic</h3>
        </div>
        <p className="text-sm text-slate-400">Follow-up scans are ranked from the latest org-scoped signals.</p>
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <section className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
          <h4 className="text-sm font-medium uppercase tracking-[0.2em] text-cyan-300/80">Follow-up Scans</h4>
          <div className="mt-4 space-y-3">
            {followUps.map((item) => (
              <div key={item.scan_type} className="rounded-xl border border-white/10 bg-slate-900/70 p-3">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm text-white">{item.scan_type}</p>
                  <span className="text-xs text-cyan-300">{item.priority}</span>
                </div>
                <p className="mt-1 text-xs text-slate-400">{item.reason}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
          <h4 className="text-sm font-medium uppercase tracking-[0.2em] text-cyan-300/80">Evolution Signals</h4>
          <p className="mt-3 text-sm text-slate-300">{evolution.evolution_reason || 'No evolution reason provided.'}</p>
          <div className="mt-4 space-y-2">
            {signals.map((signal) => (
              <div key={signal} className="rounded-xl border border-white/10 bg-slate-900/70 px-3 py-2 text-xs text-slate-300">{signal}</div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
