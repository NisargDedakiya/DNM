import React from 'react';

export default function WebhookManager({ webhooks = [], onAddWebhook, onRetryWebhook }) {
  return (
    <div className="rounded-3xl border border-white/10 bg-slate-950/80 p-6 text-slate-100 shadow-2xl shadow-cyan-950/20">
      <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.35em] text-cyan-300/80">Automation</p>
          <h3 className="text-xl font-semibold text-white">Webhook manager</h3>
        </div>
        <button onClick={onAddWebhook} className="rounded-full bg-white px-4 py-2 text-sm font-medium text-slate-950">Register webhook</button>
      </div>

      <div className="mt-5 space-y-3">
        {webhooks.map((hook) => (
          <div key={hook.id} className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
            <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="text-sm font-medium text-white">{hook.endpoint}</p>
                <p className="text-xs text-slate-400">{hook.subscribed_events?.join(', ') || 'All events'}</p>
              </div>
              <div className="text-xs text-slate-400">
                <p>Deliveries: {hook.delivery_count ?? 0}</p>
                <p>Retries: {hook.retry_count ?? 0}</p>
              </div>
            </div>
            <div className="mt-3 flex justify-end">
              <button onClick={() => onRetryWebhook?.(hook)} className="rounded-full border border-white/10 px-3 py-1 text-xs text-cyan-300">Retry</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
