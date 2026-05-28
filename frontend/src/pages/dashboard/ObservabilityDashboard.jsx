import React, { useState, useEffect } from 'react';
import { Card, Badge, Button, Spinner } from '../../components/ui/components';
import { useAuthStore } from '../../stores/authStore';
import huntApi from '../../services/huntApi';

export const ObservabilityDashboard = () => {
  const { organization } = useAuthStore();
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!organization?.id) return;
    
    const fetchMetrics = async () => {
      try {
        // Simulated or actual api hit to retrieve metrics payload
        const res = await fetch(`/api/observability/metrics?org_id=${organization.id}`, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
          }
        });
        const data = await res.json();
        setMetrics(data);
      } catch (err) {
        console.error('Failed to load observability metrics:', err);
      } finally {
        setLoading(false);
      }
    };
    
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 5000);
    return () => clearInterval(interval);
  }, [organization?.id]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-slate-950">
        <Spinner className="w-10 h-10 text-cyan-400" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-300 p-6">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-cyan-400 mb-2">⚡ System Observability</h1>
        <p className="text-slate-400">Realtime latency tracking, telemetry feeds, and event logs</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        {/* AI Performance */}
        <Card glowHover={true}>
          <h3 className="text-lg font-semibold text-purple-400 mb-4">AI Latency & Tokens</h3>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-slate-500">Avg Latency</span>
              <span className="text-purple-300 font-mono">{metrics?.ai_metrics?.latency_avg || 0}s</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Total Tokens</span>
              <span className="text-purple-300 font-mono">{metrics?.ai_metrics?.total_tokens || 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Cache Hit Ratio</span>
              <span className="text-purple-300 font-mono">{(metrics?.ai_metrics?.cache_hit_rate * 100).toFixed(0)}%</span>
            </div>
          </div>
        </Card>

        {/* Realtime Event traces */}
        <Card glowHover={true}>
          <h3 className="text-lg font-semibold text-cyan-400 mb-4">WebSocket Health</h3>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-slate-500">Status</span>
              <Badge variant="success">{metrics?.websocket_health?.status || 'Active'}</Badge>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Active Links</span>
              <span className="text-cyan-300 font-mono">{metrics?.websocket_health?.active_connections || 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Events Routed</span>
              <span className="text-cyan-300 font-mono">{metrics?.websocket_health?.messages_processed || 0}</span>
            </div>
          </div>
        </Card>

        {/* Worker heartbeats */}
        <Card glowHover={true}>
          <h3 className="text-lg font-semibold text-blue-400 mb-4">Worker Clusters</h3>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-slate-500">Active Regions</span>
              <span className="text-blue-300 font-mono">{metrics?.worker_health?.active_region || 'N/A'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Capacity Load</span>
              <span className="text-blue-300 font-mono">{metrics?.worker_health?.load_percent || 0}%</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Global State</span>
              <Badge variant="outline">{metrics?.worker_health?.status?.toUpperCase() || 'IDLE'}</Badge>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
};

export default ObservabilityDashboard;
