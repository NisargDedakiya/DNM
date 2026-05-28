import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Badge, Button } from '../../components/ui/components';
import { motion, AnimatePresence } from 'framer-motion';
import useAuthStore from '../../stores/authStore';
import useRealtimeStore from '../../store/useRealtimeStore';
import AddBugcrowdModal from '../../components/AddBugcrowdModal';
// @ts-ignore
import ExposureTimelineView from '../../timeline/ExposureTimelineView';
// @ts-ignore
import SystemHealthDashboard from '../../monitoring/SystemHealthDashboard';
// @ts-ignore
import PerformanceDashboard from '../../performance/PerformanceDashboard';

export default function Dashboard() {
  const navigate = useNavigate();
  const organizationId = useAuthStore((state) => state.user?.organization_id || '');
  const [showBugcrowdModal, setShowBugcrowdModal] = useState(false);

  // Realtime stores
  const isConnected = useRealtimeStore((state) => state.isConnected);
  const activeAlerts = useRealtimeStore((state) => state.activeAlerts);
  const recentEvents = useRealtimeStore((state) => state.recentEvents);
  
  // Local state to keep track of toast alerts
  const [activeToast, setActiveToast] = useState<any | null>(null);

  // Trigger floating toast when a new active alert arrives
  useEffect(() => {
    if (activeAlerts && activeAlerts.length > 0) {
      const latest = activeAlerts[0];
      setActiveToast(latest);
      const timer = setTimeout(() => {
        setActiveToast(null);
      }, 5000); // clear after 5s
      return () => clearTimeout(timer);
    }
  }, [activeAlerts]);

  // Simulated initial metrics
  const statsSummary = {
    scannedTargets: 1420,
    criticalFindings: 12,
    activeHunts: 3,
    integrityRate: '99.8%'
  };

  // Mock campaigns list for offensive dashboard controls
  const playbooks = [
    { name: 'External Port Penetration Sim', status: 'idle', count: 120 },
    { name: 'OIDC Session Boundary Scan', status: 'running', count: 85 },
    { name: 'SSO Trust Path Simulation', status: 'pending', count: 42 },
  ];

  return (
    <div className="space-y-6">
      {/* Realtime Floating Critical Alert Toast */}
      <AnimatePresence>
        {activeToast && (
          <motion.div
            initial={{ opacity: 0, y: -50, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -20, scale: 0.95 }}
            className="fixed top-6 right-6 z-50 w-96 p-4 rounded-xl border border-red-500 bg-[#0F0813]/95 shadow-[0_0_25px_rgba(239,68,68,0.4)] animate-border-pulse"
          >
            <div className="flex justify-between items-start">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-red-500 animate-ping"></span>
                <span className="text-xs uppercase font-mono tracking-[0.24em] text-red-400 font-bold">
                  CRITICAL INCIDENT DETECTED
                </span>
              </div>
              <button onClick={() => setActiveToast(null)} className="text-gray-400 hover:text-white">
                ✕
              </button>
            </div>
            <p className="mt-3 text-sm text-white font-semibold font-mono">
              {activeToast.title || activeToast.description || 'Intruder threat indicator observed.'}
            </p>
            {activeToast.correlation_id && (
              <p className="text-[10px] text-gray-500 font-mono mt-2">
                Trace ID: {activeToast.correlation_id}
              </p>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Header Row */}
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <div className="flex items-center space-x-3 mb-1">
            <h1 className="text-3xl font-bold tracking-wider text-white">🛡 Cyber Intelligence Command Center</h1>
            <Badge variant={isConnected ? 'primary' : 'outline'} className="animate-pulse">
              {isConnected ? 'LIVE TELEMETRY' : 'CONNECTING EVENT BUS...'}
            </Badge>
          </div>
          <p className="text-gray-400 text-sm">
            NisargHunter AI Distributed Realtime Operations Console. Monitoring active attack vectors, scopes, and campaigns.
          </p>
        </div>
        <div className="flex items-center space-x-2 text-xs font-mono bg-white/[0.02] border border-white/10 rounded-lg p-2">
          <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-400' : 'bg-yellow-500'} animate-ping`}></span>
          <span>Websocket: {isConnected ? 'Synchronized' : 'Reconnecting'}</span>
        </div>
      </div>

      {/* High-Density Stats Bar */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="rounded-xl border border-white/5 bg-slate-950/70 p-4 relative overflow-hidden group">
          <div className="absolute top-0 right-0 p-3 text-cyan-400 opacity-20 text-4xl">🕸</div>
          <div className="text-[10px] uppercase font-semibold tracking-widest text-slate-400">Scanned Targets</div>
          <div className="mt-2 text-3xl font-bold text-white glow-primary">{statsSummary.scannedTargets}</div>
          <div className="text-[9px] text-gray-500 font-mono mt-1">active assets mapped</div>
        </div>
        <div className="rounded-xl border border-white/5 bg-slate-950/70 p-4 relative overflow-hidden group">
          <div className="absolute top-0 right-0 p-3 text-red-500 opacity-20 text-4xl">⚡</div>
          <div className="text-[10px] uppercase font-semibold tracking-widest text-slate-400">Active Vulnerabilities</div>
          <div className="mt-2 text-3xl font-bold text-red-400">{statsSummary.criticalFindings}</div>
          <div className="text-[9px] text-gray-500 font-mono mt-1">critical/high severity</div>
        </div>
        <div className="rounded-xl border border-white/5 bg-slate-950/70 p-4 relative overflow-hidden group">
          <div className="absolute top-0 right-0 p-3 text-orange-400 opacity-20 text-4xl">🎯</div>
          <div className="text-[10px] uppercase font-semibold tracking-widest text-slate-400">Hunt Campaigns</div>
          <div className="mt-2 text-3xl font-bold text-orange-400">{statsSummary.activeHunts}</div>
          <div className="text-[9px] text-gray-500 font-mono mt-1">AI-driven search rooms</div>
        </div>
        <div className="rounded-xl border border-white/5 bg-slate-950/70 p-4 relative overflow-hidden group">
          <div className="absolute top-0 right-0 p-3 text-purple-400 opacity-20 text-4xl">🔄</div>
          <div className="text-[10px] uppercase font-semibold tracking-widest text-slate-400">Event Bus Integrity</div>
          <div className="mt-2 text-3xl font-bold text-purple-400">{statsSummary.integrityRate}</div>
          <div className="text-[9px] text-gray-500 font-mono mt-1">delivery delivery success</div>
        </div>
      </div>

      {/* Grid: Live Telemetry & Offensive Playbooks */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        
        {/* Telemetry Stream Console */}
        <Card className="xl:col-span-2 flex flex-col p-4 bg-[#070912] border-white/10 rounded-2xl h-[380px] overflow-hidden">
          <div className="flex items-center justify-between border-b border-white/5 pb-2 mb-3">
            <h3 className="text-xs uppercase font-mono tracking-widest text-cyan-400 flex items-center gap-2">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-cyan-500"></span>
              </span>
              REALTIME EVENT BUS TELEMETRY FEED
            </h3>
            <span className="text-[10px] font-mono text-gray-500">Ctrl + K / Cmd + K for Command Palette</span>
          </div>

          {/* Scrolling log console */}
          <div className="flex-1 overflow-y-auto custom-scrollbar font-mono text-[11px] space-y-2 bg-black/60 p-3 rounded-lg border border-white/5">
            {recentEvents.length === 0 ? (
              <div className="text-gray-600 text-center py-20">
                &gt; SYSTEM IDLE. WAITING FOR WEBSOCKET PAYLOADS...
              </div>
            ) : (
              recentEvents.map((evt: any, idx: number) => (
                <div key={idx} className="flex flex-col border-b border-white/[0.03] pb-1">
                  <div className="flex justify-between items-start text-slate-400">
                    <span className="text-[#9D4DFF] font-semibold">&gt; {evt.type || evt.event || 'EVENT'}</span>
                    <span>{evt.timestamp ? new Date(evt.timestamp).toLocaleTimeString() : new Date().toLocaleTimeString()}</span>
                  </div>
                  {evt.correlation_id && (
                    <div className="text-[10px] text-cyan-500/80">Trace Ref: {evt.correlation_id}</div>
                  )}
                  <div className="text-gray-300 ml-2 mt-0.5 whitespace-pre-wrap max-w-full break-all">
                    {JSON.stringify(evt.data || evt.payload || evt)}
                  </div>
                </div>
              ))
            )}
          </div>
        </Card>

        {/* Offensive Operations Control Deck */}
        <Card className="p-5">
          <h3 className="text-md font-semibold text-white mb-4 border-b border-white/5 pb-2">Operations Control Deck</h3>
          
          <div className="space-y-4">
            {playbooks.map((p, idx) => (
              <div key={idx} className="p-3 rounded-xl border border-white/5 bg-white/[0.02] flex justify-between items-center hover:border-white/10 transition-colors">
                <div>
                  <h4 className="text-sm font-bold text-slate-200">{p.name}</h4>
                  <div className="flex items-center gap-2 mt-1 text-[10px] text-gray-400 font-mono">
                    <span>{p.count} nodes checked</span>
                    <span>•</span>
                    <span className="uppercase text-cyan-400">{p.status}</span>
                  </div>
                </div>
                <Badge variant={p.status === 'running' ? 'primary' : 'outline'} className="text-[10px]">
                  {p.status === 'running' ? 'Active' : 'Stage'}
                </Badge>
              </div>
            ))}
          </div>

          <div className="mt-5 pt-3 border-t border-white/5 grid grid-cols-2 gap-2">
            <Button variant="outline" className="text-xs" onClick={() => navigate('/app/hunts')}>
              🎯 Setup Hunt
            </Button>
            <Button variant="primary" className="text-xs" onClick={() => setShowBugcrowdModal(true)}>
              ➕ Add Scope
            </Button>
          </div>
        </Card>
      </div>

      {/* Exposure Timeline & System Observability Panels */}
      {organizationId && (
        <div className="grid grid-cols-1 gap-6">
          
          <ExposureTimelineView organizationId={organizationId} />
          
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <PerformanceDashboard organizationId={organizationId} />
            <SystemHealthDashboard organizationId={organizationId} />
          </div>
        </div>
      )}

      {/* Add Bugcrowd Scope Modal */}
      <AddBugcrowdModal
        isOpen={showBugcrowdModal}
        onClose={() => setShowBugcrowdModal(false)}
        onSuccess={() => {
          window.location.reload();
        }}
      />
    </div>
  );
}
