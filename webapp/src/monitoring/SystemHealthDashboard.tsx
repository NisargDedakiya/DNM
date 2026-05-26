import React from 'react';

const SystemHealthDashboard: React.FC<{ organizationId: string }> = ({ organizationId }) => {
  return (
    <section className="rounded-3xl border border-white/10 bg-white/[0.03] p-5 text-white">
      <h3 className="text-lg font-semibold">System health dashboard</h3>
      <p className="mt-1 text-sm text-slate-400">Realtime observability snapshot for {organizationId}.</p>
    </section>
  );
};

export default SystemHealthDashboard;
