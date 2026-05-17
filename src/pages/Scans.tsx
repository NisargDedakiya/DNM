import React, { useEffect, useState } from "react";
import api from "../api/client";
import { useWebSocket } from "../hooks/useWebSocket";

const Scans: React.FC = () => {
  const [scans, setScans] = useState<any[]>([]);

  const fetch = async () => {
    try {
      const r = await api.get("/scans");
      setScans(r.data || []);
    } catch (e) {}
  };

  useEffect(() => { fetch(); }, []);

  useWebSocket("/ws", {
    onMessage: (data) => {
      if (data.event === 'scan_progress' || data.event === 'scan_completed') {
        // refresh or update minimal state
        fetch();
      }
    },
  });

  return (
    <div>
      <h1 className="text-2xl mb-4">Scans</h1>
      <ul className="space-y-2">
        {scans.map(s => (
          <li key={s.id} className="p-3 bg-white rounded shadow">
            <div className="flex justify-between">
              <div>
                <div className="font-semibold">{s.scan_type}</div>
                <div className="text-sm text-gray-600">Status: {s.status}</div>
              </div>
              <div>{s.started_at ? new Date(s.started_at).toLocaleString() : '-'}</div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default Scans;
