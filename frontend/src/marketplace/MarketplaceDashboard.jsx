import React from 'react';

export default function MarketplaceDashboard({ summary = {}, featuredPlugins = [], featuredConnectors = [], installationActivity = [] }) {
  return (
    <div className="space-y-6 rounded-3xl border border-white/10 bg-slate-950/90 p-6 text-slate-100 shadow-2xl shadow-cyan-950/20 backdrop-blur">
      <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.35em] text-cyan-300/80">Marketplace</p>
          <h2 className="text-2xl font-semibold text-white">Plugin and integration ecosystem</h2>
        </div>
        <p className="max-w-2xl text-sm text-slate-400">Discover validated plugins, manage connector health, and stage workflow extensions without exposing secrets or cross-org data.</p>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        {[
          ['Plugins', summary.plugins],
          ['Installations', summary.installations],
          ['Connectors', summary.connectors],
          ['Workflow Runs', summary.workflowRuns],
        ].map(([label, value]) => (
          <div key={label} className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
            <p className="text-xs uppercase tracking-[0.2em] text-slate-400">{label}</p>
            <p className="mt-3 text-3xl font-semibold text-white">{value ?? 0}</p>
          </div>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
          <h3 className="text-sm font-medium uppercase tracking-[0.2em] text-cyan-300/80">Featured Plugins</h3>
          <div className="mt-4 space-y-3">
            {featuredPlugins.map((plugin) => (
              <div key={plugin.id} className="rounded-xl border border-white/10 bg-slate-900/70 p-3">
                <div className="flex items-center justify-between gap-2">
                  <div>
                    <p className="text-sm font-medium text-white">{plugin.name}</p>
                    <p className="text-xs text-slate-400">v{plugin.version}</p>
                  </div>
                  <span className="text-xs text-cyan-300">{(plugin.permissions || []).length} permissions</span>
                </div>
                <p className="mt-2 text-xs text-slate-400">{plugin.description || 'Validated marketplace plugin'}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
          <h3 className="text-sm font-medium uppercase tracking-[0.2em] text-cyan-300/80">Connector Health</h3>
          <div className="mt-4 space-y-3">
            {featuredConnectors.map((connector) => (
              <div key={connector.id} className="rounded-xl border border-white/10 bg-slate-900/70 p-3">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm font-medium text-white">{connector.connector_type}</p>
                  <span className={`text-xs ${connector.enabled ? 'text-emerald-300' : 'text-amber-300'}`}>{connector.enabled ? 'enabled' : 'disabled'}</span>
                </div>
                <p className="mt-2 text-xs text-slate-400">{connector.configuration?.target_system || connector.configuration?.channel || 'Configured for org-scoped automation'}</p>
              </div>
            ))}
          </div>
        </section>
      </div>

      <section className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
        <h3 className="text-sm font-medium uppercase tracking-[0.2em] text-cyan-300/80">Install Activity</h3>
        <div className="mt-4 grid gap-3 md:grid-cols-3 xl:grid-cols-6">
          {installationActivity.map((item) => (
            <div key={item.label} className="rounded-xl border border-white/10 bg-slate-900/70 p-3">
              <p className="text-xs text-slate-400">{item.label}</p>
              <p className="mt-2 text-xl font-semibold text-white">{item.value}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
