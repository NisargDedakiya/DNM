import React from 'react';

const PerformanceDashboard: React.FC<{ organizationId: string }> = ({ organizationId }) => {
  return (
    <section className="rounded-3xl border border-white/10 bg-white/[0.03] p-5 text-white">
      <h3 className="text-lg font-semibold">Performance dashboard</h3>
      <p className="mt-1 text-sm text-slate-400">Cloud-native optimization summary for {organizationId}.</p>
    </section>
  );
};

export default PerformanceDashboard;
