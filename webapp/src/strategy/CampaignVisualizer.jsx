import React from 'react';

export default function CampaignVisualizer({ campaigns = [], steps = [], lifecycle = [] }) {
  return (
    <div className="rounded-3xl border border-white/10 bg-slate-950/90 p-6 text-slate-100 shadow-2xl shadow-cyan-950/20">
      <div className="flex items-end justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.35em] text-cyan-300/80">Campaign View</p>
          <h3 className="text-xl font-semibold text-white">Autonomous campaign timeline</h3>
        </div>
        <p className="text-sm text-slate-400">Approval-gated recon sequencing and lifecycle visibility.</p>
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-[1.4fr_1fr]">
        <div className="space-y-3">
          {campaigns.map((campaign) => (
            <div key={campaign.id} className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
              <div className="flex items-center justify-between gap-2">
                <div>
                  <p className="text-sm font-medium text-white">{campaign.campaign_name}</p>
                  <p className="text-xs text-slate-400">{campaign.status}</p>
                </div>
                <span className="rounded-full border border-white/10 px-3 py-1 text-xs text-cyan-300">{campaign.created_at || 'now'}</span>
              </div>
              <div className="mt-3 grid gap-2 md:grid-cols-2">
                {(campaign.methodology?.playbook?.sequence || steps).map((step) => (
                  <div key={`${campaign.id}-${step.step || step.phase}`} className="rounded-xl border border-white/10 bg-slate-900/70 p-3 text-xs text-slate-300">
                    <p className="text-white">{step.phase || step.phase_name || step.tool || `Step ${step.step}`}</p>
                    <p className="mt-1 text-slate-400">{step.rationale || step.purpose || step.scan_type || ''}</p>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
          <h4 className="text-sm font-medium uppercase tracking-[0.2em] text-cyan-300/80">Lifecycle</h4>
          <div className="mt-4 space-y-3">
            {lifecycle.map((item) => (
              <div key={item.label} className="rounded-xl border border-white/10 bg-slate-900/70 p-3">
                <p className="text-sm text-white">{item.label}</p>
                <p className="mt-1 text-xs text-slate-400">{item.detail}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
