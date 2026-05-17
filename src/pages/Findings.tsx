import React, { useEffect, useState } from "react";
import api from "../api/client";

const Findings: React.FC = () => {
  const [findings, setFindings] = useState<any[]>([]);
  const [programId, setProgramId] = useState<string>("");
  const [severity, setSeverity] = useState<string>("");

  const fetch = async () => {
    if (!programId) return;
    try {
      const params: any = { program_id: programId };
      if (severity) params.severity = severity;
      const r = await api.get("/findings", { params });
      setFindings(r.data.findings || []);
    } catch (e) {}
  };

  useEffect(() => { /* no-op */ }, []);

  return (
    <div>
      <h1 className="text-2xl mb-4">Findings</h1>
      <div className="mb-4 bg-white p-4 rounded shadow">
        <input placeholder="Program ID" value={programId} onChange={(e)=>setProgramId(e.target.value)} className="border p-2 mb-2 w-full" />
        <select value={severity} onChange={(e)=>setSeverity(e.target.value)} className="border p-2 mb-2 w-full">
          <option value="">All severities</option>
          <option value="info">info</option>
          <option value="low">low</option>
          <option value="medium">medium</option>
          <option value="high">high</option>
          <option value="critical">critical</option>
        </select>
        <button onClick={fetch} className="bg-blue-600 text-white px-3 py-1 rounded">Load</button>
      </div>

      <table className="w-full bg-white rounded shadow">
        <thead>
          <tr className="text-left p-2"><th>Title</th><th>Severity</th><th>Endpoint</th></tr>
        </thead>
        <tbody>
          {findings.map(f => (
            <tr key={f.id} className="border-t"><td className="p-2">{f.title}</td><td className="p-2">{f.severity}</td><td className="p-2">{f.endpoint}</td></tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default Findings;
