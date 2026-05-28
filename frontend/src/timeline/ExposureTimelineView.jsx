import React, { useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { Badge, Card, EmptyState, Spinner } from '../components/ui/components';
import websocket from '../realtime/websocketManager';
import { getExposureTimeline } from '../api/clients/timeline';
import RiskEvolutionChart from './RiskEvolutionChart';
import AssetDriftPanel from './AssetDriftPanel';
import ExposureRegressionAlerts from './ExposureRegressionAlerts';

const exposureEventTypes = new Set([
  'exposure.snapshot',
  'exposure.drift',
  'exposure.risk_evolution',
  'exposure.regression',
]);

const ExposureTimelineView = ({ organizationId, asset }) => {
  const [timeline, setTimeline] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [recentEvents, setRecentEvents] = useState([]);

  useEffect(() => {
    if (!organizationId) return;

    let cancelled = false;

    const loadTimeline = async () => {
      setLoading(true);
      try {
        const data = await getExposureTimeline(organizationId, { asset, limit: 60 });
        if (!cancelled) {
          setTimeline(data);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError('Failed to load exposure timeline');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    loadTimeline();
    return () => {
      cancelled = true;
    };
  }, [organizationId, asset]);

  useEffect(() => {
    if (!organizationId) return undefined;

    return websocket.on('message', (event) => {
      const eventType = event?.type || event?.event_type;
      const payload = event?.data || event?.payload || event;
      if (!eventType || !exposureEventTypes.has(eventType)) return;
      if (payload?.organization_id && payload.organization_id !== organizationId) return;
      if (asset && payload?.asset && payload.asset !== asset) return;

      setRecentEvents((current) => [
        {
          eventType,
          payload,
          timestamp: new Date().toISOString(),
        },
        ...current,
      ].slice(0, 8));

      getExposureTimeline(organizationId, { asset, limit: 60 })
        .then((data) => setTimeline(data))
        .catch(() => undefined);
    });
  }, [organizationId, asset]);

  const riskSeries = useMemo(() => {
    return (timeline?.risk_history?.history || []).map((item) => ({
      time: new Date(item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      risk: item.current_risk,
      delta: item.delta,
      summary: item.summary,
    }));
  }, [timeline]);

  const summary = timeline?.summary || {
    total_exposures: 0,
    high_risk_exposures: 0,
    drift_severity: 'info',
    risk_direction: 'stable',
    regression_count: 0,
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="text-center space-y-3">
          <Spinner className="w-6 h-6 text-cyan-400 mx-auto" />
          <p className="text-sm text-slate-400">Loading exposure timeline...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <EmptyState
        title="Exposure timeline unavailable"
        subtitle={error}
      />
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold text-white">Exposure Timeline</h2>
          <p className="text-sm text-slate-400 mt-1">
            Continuous exposure intelligence, drift tracking, and regression detection.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge variant="primary">{summary.total_exposures} exposures</Badge>
          <Badge variant="high">{summary.high_risk_exposures} high risk</Badge>
          <Badge variant={summary.risk_direction === 'escalating' ? 'critical' : 'success'}>
            {summary.risk_direction}
          </Badge>
          <Badge variant="outline">{summary.drift_severity} drift</Badge>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}>
          <Card glowHover className="h-full">
            <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Current risk</div>
            <div className="mt-3 text-4xl font-semibold text-white">{timeline?.snapshot?.risk_score?.toFixed?.(1) ?? '0.0'}</div>
            <p className="mt-2 text-sm text-slate-400">Snapshot {timeline?.snapshot?.id?.slice?.(0, 8) || 'pending'}</p>
          </Card>
        </motion.div>
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
          <Card glowHover className="h-full">
            <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Regressions</div>
            <div className="mt-3 text-4xl font-semibold text-white">{summary.regression_count}</div>
            <p className="mt-2 text-sm text-slate-400">Reintroduced or repeated risky states</p>
          </Card>
        </motion.div>
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
          <Card glowHover className="h-full">
            <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Latest signal</div>
            <div className="mt-3 text-lg font-medium text-cyan-300 capitalize">
              {summary.risk_direction || 'stable'}
            </div>
            <p className="mt-2 text-sm text-slate-400">Realtime exposure stream is active.</p>
          </Card>
        </motion.div>
      </div>

      <Card glowHover>
        <div className="flex items-center justify-between gap-4 mb-4">
          <div>
            <h3 className="text-lg font-semibold text-white">Risk Evolution Over Time</h3>
            <p className="text-sm text-slate-400">Historical risk movements for the selected scope.</p>
          </div>
          <Badge variant="outline">{riskSeries.length} points</Badge>
        </div>

        <div className="h-72">
          {riskSeries.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={riskSeries}>
                <defs>
                  <linearGradient id="riskFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#00B8FF" stopOpacity={0.35} />
                    <stop offset="95%" stopColor="#00B8FF" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="rgba(255,255,255,0.06)" strokeDasharray="3 3" />
                <XAxis dataKey="time" stroke="rgba(255,255,255,0.35)" tickLine={false} axisLine={false} />
                <YAxis stroke="rgba(255,255,255,0.35)" tickLine={false} axisLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0A1020',
                    border: '1px solid rgba(255,255,255,0.08)',
                    borderRadius: '12px',
                    color: '#E2E8F0',
                  }}
                />
                <Area type="monotone" dataKey="risk" stroke="#00B8FF" fill="url(#riskFill)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <EmptyState
              title="No risk history yet"
              subtitle="Create a few exposure snapshots to populate the timeline."
            />
          )}
        </div>
      </Card>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <RiskEvolutionChart organizationId={organizationId} asset={asset} />
        <AssetDriftPanel organizationId={organizationId} asset={asset} />
      </div>

      <ExposureRegressionAlerts organizationId={organizationId} asset={asset} />

      <Card>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-white">Realtime Exposure Feed</h3>
            <p className="text-sm text-slate-400">Recent exposure timeline events received from the websocket bus.</p>
          </div>
          <Badge variant="success">Live</Badge>
        </div>
        <div className="space-y-3">
          {recentEvents.length === 0 ? (
            <p className="text-sm text-slate-500">Waiting for exposure events.</p>
          ) : (
            recentEvents.map((item, index) => (
              <div key={`${item.eventType}-${index}`} className="rounded-lg border border-white/5 bg-white/5 p-3">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <div className="text-sm font-medium text-white">{item.eventType}</div>
                    <div className="text-xs text-slate-400">{item.payload?.asset || asset || 'organization scope'}</div>
                  </div>
                  <span className="text-xs text-slate-500 font-mono">{new Date(item.timestamp).toLocaleTimeString()}</span>
                </div>
              </div>
            ))
          )}
        </div>
      </Card>
    </div>
  );
};

export default ExposureTimelineView;
