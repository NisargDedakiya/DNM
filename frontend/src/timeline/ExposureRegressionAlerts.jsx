import React, { useEffect, useState } from 'react';
import { Badge, Card, EmptyState, Spinner } from '../components/ui/components';
import websocket from '../realtime/websocketManager';
import { getExposureRegressions } from '../api/clients/timeline';

const ExposureRegressionAlerts = ({ organizationId, asset }) => {
  const [regressions, setRegressions] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!organizationId) return undefined;

    let cancelled = false;
    setLoading(true);

    getExposureRegressions(organizationId, { asset, limit: 30 })
      .then((result) => {
        if (!cancelled) setRegressions(result);
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
      if (eventType !== 'exposure.regression') return;
      if (payload?.organization_id && payload.organization_id !== organizationId) return;
      if (asset && payload?.asset && payload.asset !== asset) return;

      getExposureRegressions(organizationId, { asset, limit: 30 }).then(setRegressions).catch(() => undefined);
    });
  }, [organizationId, asset]);

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
          <h3 className="text-lg font-semibold text-white">Exposure Regression Alerts</h3>
          <p className="text-sm text-slate-400">Repeated risky exposure states and reintroduced issues.</p>
        </div>
        <Badge variant={regressions?.regression_count > 0 ? 'critical' : 'success'}>
          {regressions?.regression_count || 0} alerts
        </Badge>
      </div>

      {(regressions?.regressions || []).length === 0 && (regressions?.repeat_exposures || []).length === 0 ? (
        <EmptyState title="No regressions detected" subtitle="The current timeline does not show repeated risky states." />
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-lg border border-white/5 bg-white/5 p-3">
              <div className="text-xs text-slate-500 uppercase tracking-[0.2em]">Repeat exposures</div>
              <div className="mt-2 text-lg font-semibold text-white">{regressions?.repeat_exposures?.length || 0}</div>
            </div>
            <div className="rounded-lg border border-white/5 bg-white/5 p-3">
              <div className="text-xs text-slate-500 uppercase tracking-[0.2em]">Recurring patterns</div>
              <div className="mt-2 text-lg font-semibold text-white">{regressions?.recurring_patterns?.length || 0}</div>
            </div>
          </div>

          <div className="space-y-3 max-h-[380px] overflow-y-auto pr-1">
            {(regressions?.regressions || []).map((item, index) => (
              <div key={`${item.key || index}`} className="rounded-lg border border-amber-500/15 bg-amber-500/5 p-3">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <div className="text-sm font-medium text-amber-100">
                      {item.current?.title || item.key || 'Regression detected'}
                    </div>
                    <div className="text-xs text-slate-400 mt-1">
                      {item.current?.risk_level || item.current?.exposure_type || 'risk state reintroduced'}
                    </div>
                  </div>
                  <Badge variant="high">Reintroduced</Badge>
                </div>
              </div>
            ))}

            {(regressions?.repeat_exposures || []).map((item, index) => (
              <div key={`${item.signature || index}`} className="rounded-lg border border-slate-700 bg-slate-900/60 p-3">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <div className="text-sm font-medium text-white">{item.example?.title || item.signature}</div>
                    <div className="text-xs text-slate-400 mt-1">Repeated {item.count} times</div>
                  </div>
                  <Badge variant="outline">Repeat</Badge>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
};

export default ExposureRegressionAlerts;
