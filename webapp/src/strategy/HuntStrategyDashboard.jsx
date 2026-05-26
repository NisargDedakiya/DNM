import React from 'react';

export default function HuntStrategyDashboard({ summary = {}, huntRecommendations = [], campaignSignals = [], methodologyHighlights = [] }) {
  return (
    <div className="space-y-6 rounded-3xl border border-white/10 bg-slate-950/90 p-6 text-slate-100 shadow-2xl shadow-cyan-950/20 backdrop-blur">
      <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.35em] text-cyan-300/80">Strategy Control</p>
          <h2 className="text-2xl font-semibold text-white">AI hunt strategy planner</h2>
        </div>
        <p className="max-w-2xl text-sm text-slate-400">Advisory hunt planning, approval-gated campaign intelligence, and org-scoped target prioritization.</p>
      </div>

      <div className="grid gap-4 md:grid-cols-3 xl:grid-cols-6">
        {[
          ['Hunts', summary.hunts],
          ['Campaigns', summary.campaigns],
          ['Priority Assets', summary.priorities],
          ['Monitoring Signals', summary.monitoringSignals],
          ['Approval Gates', summary.approvalGates],
          ['Adaptive Cycles', summary.adaptiveCycles],
        ].map(([label, value]) => (
          <div key={label} className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
            <p className="text-xs uppercase tracking-[0.2em] text-slate-400">{label}</p>
            <p className="mt-3 text-3xl font-semibold text-white">{value ?? 0}</p>
          </div>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
          <h3 className="text-sm font-medium uppercase tracking-[0.2em] text-cyan-300/80">Hunt Recommendations</h3>
          <div className="mt-4 space-y-3">
            {huntRecommendations.slice(0, 5).map((item) => (
              <div key={item.id ?? item.name} className="rounded-xl border border-white/10 bg-slate-900/70 p-3">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm font-medium text-white">{item.name || item.hostname || item.asset}</p>
                  <span className="text-xs text-cyan-300">{item.priority_score?.toFixed?.(2) ?? item.priority_score ?? 0}</span>
                </div>
                <p className="mt-1 text-xs text-slate-400">{item.priority_reason || item.advisory_note || 'Org-scoped priority target'}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
          <h3 className="text-sm font-medium uppercase tracking-[0.2em] text-cyan-300/80">Campaign Signals</h3>
          <div className="mt-4 space-y-3">
            {campaignSignals.slice(0, 5).map((item) => (
              <div key={item.id ?? item.campaign_name} className="rounded-xl border border-white/10 bg-slate-900/70 p-3">
                <div className="flex items-center justify-between gap-2 text-white">
                  <p className="text-sm font-medium">{item.campaign_name || item.name}</p>
                  <span className="text-xs text-emerald-300">{item.status || 'pending_approval'}</span>
                </div>
                <p className="mt-1 text-xs text-slate-400">{item.methodology?.playbook?.objective || item.methodology?.objective || 'Approval-gated campaign intelligence'}</p>
              </div>
            ))}
          </div>
        </section>
      </div>

      <section className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
        <h3 className="text-sm font-medium uppercase tracking-[0.2em] text-cyan-300/80">Methodology Highlights</h3>
        <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {methodologyHighlights.map((item) => (
            <div key={item.title} className="rounded-xl border border-white/10 bg-slate-900/70 p-3">
              <p className="text-xs text-slate-400">{item.title}</p>
              <p className="mt-2 text-sm text-white">{item.body}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
