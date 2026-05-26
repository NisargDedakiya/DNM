import React, { useEffect, useState } from 'react';
import { Badge, Card, EmptyState, Spinner } from '../components/ui/components';
import websocket from '../services/websocket';
import { getExposureDrift } from '../api/clients/timeline';

const severityVariant = (severity) => {
  switch ((severity || '').toLowerCase()) {
    case 'critical':
      return 'critical';
    case 'high':
      return 'high';
    case 'medium':
      return 'medium';
    default:
      return 'outline';
  }
};

const AssetDriftPanel = ({ organizationId, asset }) => {
  const [drift, setDrift] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!organizationId) return undefined;

    let cancelled = false;
    setLoading(true);

    getExposureDrift(organizationId, { asset, limit: 40 })
      .then((result) => {
        if (!cancelled) setDrift(result);
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

    const token = localStorage.getItem('auth_token') || localStorage.getItem('authToken');
    const websocketOrgId = localStorage.getItem('org_id') || localStorage.getItem('organizationId') || organizationId;

    if (token && websocketOrgId && !websocket.getStatus().isConnected) {
      websocket.connect(token, websocketOrgId).catch(() => undefined);
    }

    return websocket.on('message', (event) => {
      const eventType = event?.type || event?.event_type;
      const payload = event?.data || event?.payload || event;
      if (eventType !== 'exposure.drift') return;
      if (payload?.organization_id && payload.organization_id !== organizationId) return;
      if (asset && payload?.asset && payload.asset !== asset) return;

      getExposureDrift(organizationId, { asset, limit: 40 }).then(setDrift).catch(() => undefined);
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

  const changes = drift?.changes || { added: [], removed: [], changed: [], summary: {} };

  return (
    <Card glowHover>
      <div className="flex items-start justify-between gap-3 mb-4">
        <div>
          <h3 className="text-lg font-semibold text-white">Asset Drift</h3>
          <p className="text-sm text-slate-400">Infrastructure drift, auth changes, and exposure mutations.</p>
        </div>
        <Badge variant={severityVariant(drift?.severity)}>{drift?.severity || 'info'}</Badge>
      </div>

      {!drift?.drift_detected ? (
        <EmptyState title="No meaningful drift detected" subtitle="The latest snapshots are stable for this scope." />
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-3">
            <div className="rounded-lg border border-white/5 bg-white/5 p-3">
              <div className="text-xs text-slate-500 uppercase tracking-[0.2em]">Added</div>
              <div className="mt-2 text-lg font-semibold text-white">{changes.summary?.added_count || 0}</div>
            </div>
            <div className="rounded-lg border border-white/5 bg-white/5 p-3">
              <div className="text-xs text-slate-500 uppercase tracking-[0.2em]">Changed</div>
              <div className="mt-2 text-lg font-semibold text-white">{changes.summary?.changed_count || 0}</div>
            </div>
            <div className="rounded-lg border border-white/5 bg-white/5 p-3">
              <div className="text-xs text-slate-500 uppercase tracking-[0.2em]">Removed</div>
              <div className="mt-2 text-lg font-semibold text-white">{changes.summary?.removed_count || 0}</div>
            </div>
          </div>

          <div className="space-y-3 max-h-[360px] overflow-y-auto pr-1">
            {(drift?.high_risk_changes || []).length === 0 ? (
              <div className="text-sm text-slate-500">No high-risk drift patterns matched the current scope.</div>
            ) : (
              drift.high_risk_changes.map((item, index) => (
                <div key={`${item.key || item.title || index}`} className="rounded-lg border border-red-500/15 bg-red-500/5 p-3">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <div className="text-sm font-medium text-red-200">
                        {item.current?.title || item.title || item.key || 'High-risk change'}
                      </div>
                      <div className="text-xs text-slate-400 mt-1">
                        {item.current?.exposure_type || item.exposure_type || 'exposure'}
                      </div>
                    </div>
                    <Badge variant="critical">{item.bucket}</Badge>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </Card>
  );
};

export default AssetDriftPanel;
