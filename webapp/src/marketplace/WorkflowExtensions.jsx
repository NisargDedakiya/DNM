import React from 'react';

export default function WorkflowExtensions({ workflows = [], onAddStep, onBindEvent }) {
  return (
    <div className="rounded-3xl border border-white/10 bg-slate-950/90 p-6 text-slate-100 shadow-2xl shadow-cyan-950/20">
      <div className="flex items-end justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.35em] text-cyan-300/80">Workflow Extensions</p>
          <h3 className="text-xl font-semibold text-white">Automation chaining</h3>
        </div>
        <div className="flex gap-2">
          <button onClick={onAddStep} className="rounded-full bg-cyan-400 px-4 py-2 text-sm font-medium text-slate-950">Add step</button>
          <button onClick={onBindEvent} className="rounded-full border border-white/10 px-4 py-2 text-sm font-medium text-white">Bind event</button>
        </div>
      </div>

      <div className="mt-5 space-y-3">
        {workflows.map((workflow) => (
          <div key={workflow.id ?? workflow.name} className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
            <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="text-sm font-medium text-white">{workflow.name}</p>
                <p className="text-xs text-slate-400">{workflow.event || 'workflow.triggered'}</p>
              </div>
              <span className="text-xs text-cyan-300">{workflow.steps?.length ?? 0} steps</span>
            </div>
            <div className="mt-3 grid gap-2 md:grid-cols-2">
              {(workflow.steps || []).map((step) => (
                <div key={step.name || step.action} className="rounded-xl border border-white/10 bg-slate-900/70 p-3 text-xs text-slate-300">
                  <p className="text-white">{step.name || step.action}</p>
                  <p className="mt-1 text-slate-400">{step.description || 'Automation step'}</p>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
