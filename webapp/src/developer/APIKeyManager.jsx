import React from 'react';

export default function APIKeyManager({ keys = [], onRotateKey, onCreateKey }) {
  return (
    <div className="rounded-3xl border border-white/10 bg-slate-950/80 p-6 text-slate-100 shadow-2xl shadow-cyan-950/20">
      <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.35em] text-cyan-300/80">API Access</p>
          <h3 className="text-xl font-semibold text-white">Key management</h3>
        </div>
        <div className="flex gap-2">
          <button onClick={onCreateKey} className="rounded-full bg-cyan-400 px-4 py-2 text-sm font-medium text-slate-950">Create Key</button>
        </div>
      </div>

      <div className="mt-5 space-y-3">
        {keys.map((key) => (
          <div key={key.id} className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
            <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="text-sm font-medium text-white">{key.name}</p>
                <p className="text-xs text-slate-400">{key.permissions?.join(', ') || 'No permissions'}</p>
              </div>
              <div className="text-right text-xs text-slate-400">
                <p>Rate limit: {key.rate_limit?.requests_per_minute ?? 'n/a'} rpm</p>
                <p>Last used: {key.last_used_at || 'never'}</p>
              </div>
            </div>
            <div className="mt-3 flex justify-end">
              <button onClick={() => onRotateKey?.(key)} className="rounded-full border border-white/10 px-3 py-1 text-xs text-cyan-300">Rotate</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
