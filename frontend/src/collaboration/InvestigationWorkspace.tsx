import React from 'react';

const InvestigationWorkspace: React.FC<{ organizationId: string; attackGraphSummary?: { nodes: number; edges: number; summary: string } }> = ({ organizationId, attackGraphSummary }) => {
  return (
    <section className="rounded-3xl border border-white/10 bg-white/[0.03] p-5 text-white">
      <h3 className="text-lg font-semibold">Investigation workspace</h3>
      <p className="mt-1 text-sm text-slate-400">Org-isolated collaboration and evidence tracking for {organizationId}.</p>
      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <div className="rounded-2xl border border-white/10 bg-slate-950/50 p-4">
          <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">Nodes</div>
          <div className="mt-2 text-2xl font-semibold">{attackGraphSummary?.nodes ?? 0}</div>
        </div>
        <div className="rounded-2xl border border-white/10 bg-slate-950/50 p-4">
          <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">Edges</div>
          <div className="mt-2 text-2xl font-semibold">{attackGraphSummary?.edges ?? 0}</div>
        </div>
        <div className="rounded-2xl border border-white/10 bg-slate-950/50 p-4">
          <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">Summary</div>
          <div className="mt-2 text-sm text-slate-300">{attackGraphSummary?.summary ?? 'Collaborate on findings in a secure workspace.'}</div>
        </div>
      </div>
    </section>
  );
};

export default InvestigationWorkspace;
