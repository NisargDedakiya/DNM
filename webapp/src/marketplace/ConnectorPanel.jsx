import React from 'react';

export default function ConnectorPanel({ connectors = [], onConfigure, onToggle }) {
  return (
    <div className="rounded-3xl border border-white/10 bg-slate-950/90 p-6 text-slate-100 shadow-2xl shadow-cyan-950/20">
      <div className="flex items-end justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.35em] text-cyan-300/80">Enterprise Integrations</p>
          <h3 className="text-xl font-semibold text-white">Connector panel</h3>
        </div>
        <button onClick={onConfigure} className="rounded-full bg-white px-4 py-2 text-sm font-medium text-slate-950">Configure connector</button>
      </div>

      <div className="mt-5 space-y-3">
        {connectors.map((connector) => (
          <div key={connector.id} className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
            <div className="flex items-center justify-between gap-2">
              <div>
                <p className="text-sm font-medium text-white">{connector.connector_type}</p>
                <p className="text-xs text-slate-400">{connector.configuration?.description || 'Org-scoped integration'}</p>
              </div>
              <span className={`text-xs ${connector.enabled ? 'text-emerald-300' : 'text-amber-300'}`}>{connector.enabled ? 'enabled' : 'disabled'}</span>
            </div>
            <div className="mt-3 flex justify-end">
              <button onClick={() => onToggle?.(connector)} className="rounded-full border border-white/10 px-3 py-1 text-xs text-cyan-300">Toggle</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
