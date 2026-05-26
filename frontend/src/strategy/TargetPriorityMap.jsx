import React from 'react';

export default function TargetPriorityMap({ targets = [] }) {
  return (
    <div className="rounded-3xl border border-white/10 bg-slate-950/90 p-6 text-slate-100 shadow-2xl shadow-cyan-950/20">
      <div>
        <p className="text-xs uppercase tracking-[0.35em] text-cyan-300/80">Target Prioritization</p>
        <h3 className="text-xl font-semibold text-white">Exploitability-aware target map</h3>
      </div>

      <div className="mt-5 space-y-3">
        {targets.map((target, index) => (
          <div key={target.id ?? target.name ?? index} className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-sm font-medium text-white">{target.name || target.hostname || target.asset}</p>
                <p className="text-xs text-slate-400">{target.priority_reason || 'Business-critical target'}</p>
              </div>
              <div className="text-right">
                <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Priority</p>
                <p className="text-lg font-semibold text-cyan-300">{target.priority_score?.toFixed?.(2) ?? target.priority_score ?? 0}</p>
              </div>
            </div>
            <div className="mt-3 grid gap-2 md:grid-cols-4 text-xs text-slate-400">
              <div>Risk {target.risk_score ?? 0}</div>
              <div>Exposures {target.exposure_score ?? 0}</div>
              <div>Threat {target.threat_score ?? 0}</div>
              <div>Signals {target.signal_score ?? 0}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
