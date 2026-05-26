import React from 'react';

export default function PluginManager({ plugins = [], onInstall, onDisable }) {
  return (
    <div className="rounded-3xl border border-white/10 bg-slate-950/90 p-6 text-slate-100 shadow-2xl shadow-cyan-950/20">
      <div className="flex items-end justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.35em] text-cyan-300/80">Installed Plugins</p>
          <h3 className="text-xl font-semibold text-white">Plugin manager</h3>
        </div>
        <button onClick={onInstall} className="rounded-full bg-cyan-400 px-4 py-2 text-sm font-medium text-slate-950">Install plugin</button>
      </div>

      <div className="mt-5 space-y-3">
        {plugins.map((plugin) => (
          <div key={plugin.id} className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
            <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="text-sm font-medium text-white">{plugin.name}</p>
                <p className="text-xs text-slate-400">Permissions: {(plugin.permissions || []).join(', ') || 'none'}</p>
              </div>
              <div className="text-right text-xs text-slate-400">
                <p>Version {plugin.version}</p>
                <p>Installed {plugin.created_at || 'recently'}</p>
              </div>
            </div>
            <div className="mt-3 flex justify-end">
              <button onClick={() => onDisable?.(plugin)} className="rounded-full border border-white/10 px-3 py-1 text-xs text-cyan-300">Disable</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
