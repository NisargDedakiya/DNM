import React, { useEffect, useMemo, useState } from 'react';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts';
import useRealtimeStore from '../store/useRealtimeStore';

const ExposureTimelineView: React.FC<{ organizationId: string }> = ({ organizationId }) => {
  const recentEvents = useRealtimeStore((state) => state.recentEvents);
  const [timelineData, setTimelineData] = useState<Array<{ name: string; value: number }>>([]);

  useEffect(() => {
    const samples = recentEvents.slice(0, 10).map((event, index) => ({
      name: `E${index + 1}`,
      value: Number(event?.latency_ms || event?.value || index + 1),
    }));
    setTimelineData(samples.length ? samples : [{ name: 'Baseline', value: 1 }]);
  }, [recentEvents, organizationId]);

  const title = useMemo(() => `Exposure timeline · ${organizationId}`, [organizationId]);

  return (
    <section className="rounded-3xl border border-white/10 bg-white/[0.03] p-5 text-white">
      <div className="mb-4">
        <h3 className="text-lg font-semibold">{title}</h3>
        <p className="text-sm text-slate-400">Realtime exposure and regression visibility.</p>
      </div>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={timelineData}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
            <XAxis dataKey="name" stroke="rgba(255,255,255,0.4)" />
            <YAxis stroke="rgba(255,255,255,0.4)" />
            <Tooltip contentStyle={{ backgroundColor: '#0b1020', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '12px', color: '#fff' }} />
            <Area type="monotone" dataKey="value" stroke="#22d3ee" fill="rgba(34,211,238,0.15)" />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
};

export default ExposureTimelineView;
