import React from 'react';

const statCards = [
  { label: 'API Keys', key: 'apiKeys' },
  { label: 'Webhooks', key: 'webhooks' },
  { label: 'Applications', key: 'applications' },
  { label: 'Realtime Events', key: 'events' },
];

export default function DeveloperDashboard({ summary = {}, webhookActivity = [], usageTimeline = [], integrationHealth = [] }) {
  return (
    <div className="space-y-6 rounded-3xl border border-white/10 bg-slate-950/80 p-6 text-slate-100 shadow-2xl shadow-cyan-950/20 backdrop-blur">
      <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.35em] text-cyan-300/80">Developer Platform</p>
          <h2 className="text-2xl font-semibold text-white">Ecosystem control plane</h2>
        </div>
        <p className="max-w-2xl text-sm text-slate-400">Public APIs, SDK integrations, webhook automation, and usage visibility with org isolation preserved.</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {statCards.map((card) => (
          <div key={card.key} className="rounded-2xl border border-white/10 bg-white/5 p-4">
            <p className="text-xs uppercase tracking-[0.2em] text-slate-400">{card.label}</p>
            <div className="mt-3 text-3xl font-semibold text-white">{summary[card.key] ?? 0}</div>
          </div>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
          <h3 className="text-sm font-medium uppercase tracking-[0.2em] text-cyan-300/80">Webhook Activity</h3>
          <div className="mt-4 space-y-3">
            {webhookActivity.slice(0, 5).map((item) => (
              <div key={item.id ?? item.endpoint} className="rounded-xl border border-white/10 bg-slate-900/70 p-3 text-sm text-slate-300">
                <div className="flex items-center justify-between gap-2 text-white">
                  <span>{item.endpoint || item.name}</span>
                  <span className="text-xs text-emerald-300">{item.status || 'delivered'}</span>
                </div>
                <p className="mt-1 text-xs text-slate-400">{item.event_type || item.subscribed_events?.join(', ') || 'realtime event'}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
          <h3 className="text-sm font-medium uppercase tracking-[0.2em] text-cyan-300/80">Integration Health</h3>
          <div className="mt-4 space-y-3">
            {integrationHealth.slice(0, 5).map((item) => (
              <div key={item.id ?? item.name} className="rounded-xl border border-white/10 bg-slate-900/70 p-3 text-sm text-slate-300">
                <div className="flex items-center justify-between gap-2 text-white">
                  <span>{item.name}</span>
                  <span className={`text-xs ${item.status === 'healthy' ? 'text-emerald-300' : 'text-amber-300'}`}>{item.status || 'unknown'}</span>
                </div>
                <p className="mt-1 text-xs text-slate-400">{item.detail || item.last_used_at || 'No recent activity'}</p>
              </div>
            ))}
          </div>
        </section>
      </div>

      <section className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
        <h3 className="text-sm font-medium uppercase tracking-[0.2em] text-cyan-300/80">Usage Trend</h3>
        <div className="mt-4 grid gap-3 md:grid-cols-3 xl:grid-cols-6">
          {usageTimeline.map((item) => (
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
