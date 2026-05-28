import React, { useEffect, useMemo, useState } from 'react';
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { Badge, Card, EmptyState, Spinner } from '../components/ui/components';
import websocket from '../realtime/websocketManager';
import { getRiskEvolution } from '../api/clients/timeline';

const RiskEvolutionChart = ({ organizationId, asset }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!organizationId) return undefined;

    let cancelled = false;
    setLoading(true);

    getRiskEvolution(organizationId, { asset, limit: 40 })
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [organizationId, asset]);

  useEffect(() => {
    if (!organizationId) return undefined;

    return websocket.on('message', (event) => {
      const eventType = event?.type || event?.event_type;
      const payload = event?.data || event?.payload || event;
      if (!eventType || !eventType.startsWith('exposure.')) return;
      if (payload?.organization_id && payload.organization_id !== organizationId) return;
      if (asset && payload?.asset && payload.asset !== asset) return;

      getRiskEvolution(organizationId, { asset, limit: 40 }).then(setData).catch(() => undefined);
    });
  }, [organizationId, asset]);

  const chartData = useMemo(() => {
    return (data?.history || [])
      .slice()
      .reverse()
      .map((item) => ({
        label: new Date(item.created_at).toLocaleDateString([], { month: 'short', day: 'numeric' }),
        risk: item.current_risk,
        previous: item.previous_risk,
        delta: item.delta,
      }));
  }, [data]);

  if (loading) {
    return (
      <Card>
        <div className="flex items-center justify-center py-10">
          <Spinner className="w-5 h-5 text-cyan-400" />
        </div>
      </Card>
    );
  }

  return (
    <Card glowHover>
      <div className="flex items-start justify-between gap-3 mb-4">
        <div>
          <h3 className="text-lg font-semibold text-white">Risk Evolution</h3>
          <p className="text-sm text-slate-400">Severity movement and escalation history.</p>
        </div>
        <Badge variant={data?.latest_risk >= 8 ? 'critical' : data?.latest_risk >= 6 ? 'high' : 'success'}>
          {data?.latest_risk?.toFixed?.(1) ?? '0.0'}
        </Badge>
      </div>

      <div className="h-64">
        {chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="riskChartFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#9D4DFF" stopOpacity={0.35} />
                  <stop offset="95%" stopColor="#9D4DFF" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="rgba(255,255,255,0.06)" strokeDasharray="3 3" />
              <XAxis dataKey="label" stroke="rgba(255,255,255,0.35)" tickLine={false} axisLine={false} />
              <YAxis stroke="rgba(255,255,255,0.35)" tickLine={false} axisLine={false} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#0A1020',
                  border: '1px solid rgba(255,255,255,0.08)',
                  borderRadius: '12px',
                  color: '#E2E8F0',
                }}
              />
              <Area type="monotone" dataKey="risk" stroke="#9D4DFF" fill="url(#riskChartFill)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <EmptyState title="No risk evolution data" subtitle="Snapshots will appear here once monitoring begins." />
        )}
      </div>

      <div className="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className="rounded-lg border border-white/5 bg-white/5 p-3">
          <div className="text-xs text-slate-500 uppercase tracking-[0.2em]">Average</div>
          <div className="mt-2 text-lg font-semibold text-white">{data?.average_risk?.toFixed?.(1) ?? '0.0'}</div>
        </div>
        <div className="rounded-lg border border-white/5 bg-white/5 p-3">
          <div className="text-xs text-slate-500 uppercase tracking-[0.2em]">Escalations</div>
          <div className="mt-2 text-lg font-semibold text-white">{data?.escalations?.length || 0}</div>
        </div>
        <div className="rounded-lg border border-white/5 bg-white/5 p-3">
          <div className="text-xs text-slate-500 uppercase tracking-[0.2em]">Latest</div>
          <div className="mt-2 text-lg font-semibold text-white">{data?.latest_risk?.toFixed?.(1) ?? '0.0'}</div>
        </div>
      </div>
    </Card>
  );
};

export default RiskEvolutionChart;
