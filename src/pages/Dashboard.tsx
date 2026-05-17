import React, { useEffect, useState } from "react";
import api from "../api/client";

const Dashboard: React.FC = () => {
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    api.get("/dashboard/stats")
      .then((r) => { if (mounted) setStats(r.data); })
      .catch(() => {})
      .finally(() => { if (mounted) setLoading(false); });
    return () => { mounted = false; };
  }, []);

  if (loading) return <div>Loading...</div>;
  if (!stats) return <div>No data</div>;

  return (
    <div>
      <h1 className="text-2xl mb-4">Dashboard</h1>
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="p-4 bg-white rounded shadow">Programs<br/><strong>{stats.total_programs}</strong></div>
        <div className="p-4 bg-white rounded shadow">Scans<br/><strong>{stats.total_scans}</strong></div>
        <div className="p-4 bg-white rounded shadow">Findings<br/><strong>{stats.total_findings}</strong></div>
        <div className="p-4 bg-white rounded shadow">Reports<br/><strong>{stats.total_reports}</strong></div>
      </div>

      <section className="mb-6">
        <h2 className="text-xl mb-2">Findings by severity</h2>
        <div className="flex gap-3">
          {Object.entries(stats.findings_by_severity || {}).map(([k,v]) => (
            <div key={k} className="p-3 bg-white rounded shadow">{k}<br/><strong>{v}</strong></div>
          ))}
        </div>
      </section>

      <section>
        <h2 className="text-xl mb-2">Recent activity</h2>
        <ul className="space-y-2">
          {(stats.recent_activity || []).map((it: any) => (
            <li key={it.id} className="p-3 bg-white rounded shadow">{it.type} - {it.title || it.meta.status}</li>
          ))}
        </ul>
      </section>
    </div>
  );
};

export default Dashboard;
