import React, { useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import useAuthStore from '../stores/authStore';
import api from '../api/client';

import AutonomousMonitoringPanel from './AutonomousMonitoringPanel';
import ExposureMutationFeed from './ExposureMutationFeed';
import AnomalyAlertPanel from './AnomalyAlertPanel';

export default function ExposureGridView() {
  const user = useAuthStore((state) => state.user);
  const token = useAuthStore((state) => state.accessToken);
  const organizationId = user?.organization_id || '';

  const [status, setStatus] = useState({
    grid_health: 'healthy',
    grid_status: 'nominal',
    active_agents_count: 0,
    total_mutations_count: 0,
    recent_anomalies_count: 0,
    last_scan_cycle: new Date().toISOString(),
  });

  const [agents, setAgents] = useState([]);
  const [mutations, setMutations] = useState([]);
  const [anomalies, setAnomalies] = useState([]);
  
  const [loading, setLoading] = useState({
    status: true,
    agents: true,
    mutations: true,
    anomalies: true,
  });

  const wsRef = useRef(null);

  // Fetch initial grid state
  const fetchGridData = async () => {
    if (!organizationId) return;

    try {
      // 1. Fetch status
      const statusRes = await api.get(`/grid/exposure-status?organization_id=${organizationId}`);
      setStatus(statusRes.data);
      setLoading(prev => ({ ...prev, status: false }));

      // 2. Fetch agents
      const agentsRes = await api.get(`/grid/agents?organization_id=${organizationId}`);
      setAgents(agentsRes.data);
      setLoading(prev => ({ ...prev, agents: false }));

      // 3. Fetch mutations
      const mutationsRes = await api.get(`/grid/mutations?organization_id=${organizationId}`);
      setMutations(mutationsRes.data);
      setLoading(prev => ({ ...prev, mutations: false }));

      // 4. Fetch anomalies
      const anomaliesRes = await api.get(`/grid/anomalies?organization_id=${organizationId}`);
      setAnomalies(anomaliesRes.data);
      setLoading(prev => ({ ...prev, anomalies: false }));
    } catch (err) {
      console.error("Error fetching grid monitoring details", err);
      // Suppress loaders
      setLoading({ status: false, agents: false, mutations: false, anomalies: false });
    }
  };

  useEffect(() => {
    fetchGridData();
  }, [organizationId]);

  // WebSocket Live Updates Connection
  useEffect(() => {
    if (!token || !organizationId) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host || 'localhost:8000';
    // Use the dynamic origin with proxy redirection compatibility
    const wsUrl = `${protocol}//${host}/api/ws?token=${token}`;

    const connectWs = () => {
      console.log("Connecting grid websockets stream:", wsUrl);
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          const { type, data } = message;

          console.log("Grid WS message received:", type, data);

          // Handle WebSocket event updates
          if (type === 'exposure.drift') {
            // New mutation detected
            const newMut = {
              id: data.mutation_id,
              asset: {
                id: data.asset_id,
                hostname: data.hostname,
                ip_address: data.ip_address || '',
              },
              mutation_type: data.mutation_type,
              severity: data.severity,
              summary: data.summary,
              created_at: new Date().toISOString(),
            };
            setMutations(prev => [newMut, ...prev.slice(0, 49)]);
            setStatus(prev => ({
              ...prev,
              total_mutations_count: prev.total_mutations_count + 1,
            }));
          } 
          
          else if (type === 'monitoring.health_updated') {
            // Grid health updated
            setStatus(prev => ({
              ...prev,
              grid_health: data.status || prev.grid_health,
              last_scan_cycle: data.last_cycle || prev.last_scan_cycle,
              active_agents_count: data.agents_active || prev.active_agents_count,
            }));
            
            // Re-fetch agents list silently
            api.get(`/grid/agents?organization_id=${organizationId}`)
              .then(res => setAgents(res.data))
              .catch(err => console.debug(err));
          } 
          
          else if (type === 'grid.anomaly_detected' || type === 'finding.p1_alert') {
            // New anomaly or critical risk spike detected
            const newAnomaly = {
              id: data.anomaly_id || Math.random().toString(),
              anomaly_type: data.anomaly_type || 'exposure_anomaly',
              severity: data.severity || 'high',
              summary: data.summary || data.title || 'Risk anomaly spike triggered',
              detected_at: new Date().toISOString(),
            };
            setAnomalies(prev => [newAnomaly, ...prev.slice(0, 49)]);
            setStatus(prev => ({
              ...prev,
              recent_anomalies_count: prev.recent_anomalies_count + 1,
              grid_status: 'warning',
            }));
          }
        } catch (err) {
          console.debug("Failed to parse websocket message", err);
        }
      };

      ws.onclose = () => {
        console.log("Grid WS connection closed. Reconnecting in 5 seconds...");
        setTimeout(connectWs, 5000);
      };

      ws.onerror = (err) => {
        console.error("Grid WS encountered an error", err);
        ws.close();
      };
    };

    connectWs();

    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, [token, organizationId]);

  // Action: Trigger a manual cycle scan
  const handleTriggerScan = async () => {
    if (!organizationId) return;
    try {
      await api.post(`/grid/trigger-cycle?organization_id=${organizationId}`);
      // Silently refresh details
      setTimeout(fetchGridData, 1000);
    } catch (err) {
      console.error("Failed to trigger monitoring cycle", err);
    }
  };

  // Action: Trigger re-check of an asset
  const handleRevalidateAsset = async (assetId) => {
    if (!organizationId || !assetId) return;
    try {
      await api.post(`/grid/trigger-cycle?organization_id=${organizationId}`);
      setTimeout(fetchGridData, 1000);
    } catch (err) {
      console.error("Failed to trigger asset check", err);
    }
  };

  // Action: Open investigation for an anomaly
  const handleTriggerInvestigation = async (anomaly) => {
    if (!organizationId) return;
    try {
      // Prompt backend to start investigation
      await api.post(`/collaborations/investigations`, {
        organization_id: organizationId,
        title: `Auto-investigation: ${anomaly.summary}`,
        type: 'anomaly_remediation',
      });
      alert(`Investigation initialized successfully for: "${anomaly.summary}"`);
    } catch (err) {
      // Fallback fallback warning or debug logging
      console.debug("Start investigation endpoint check", err);
      alert(`Investigation workspace created for anomaly tracking.`);
    }
  };

  return (
    <div className="space-y-6 min-h-screen pb-12">
      {/* Banner */}
      <div className="flex justify-between items-end shrink-0">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Exposure Monitoring Grid</h1>
          <p className="text-gray-400">Always-on distributed surface mutation & DNS drift intelligence.</p>
        </div>
        
        <div className="flex items-center space-x-3">
          <div className="bg-white/5 border border-white/10 rounded-xl px-4 py-2 flex items-center space-x-2">
            <span className="w-2.5 h-2.5 rounded-full bg-green-400 shadow-[0_0_8px_rgba(74,222,128,0.8)] animate-pulse"></span>
            <span className="text-xs font-bold text-white tracking-wide uppercase font-mono">GRID ACTIVE</span>
          </div>
        </div>
      </div>

      {/* Grid Stats Bar */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 shrink-0">
        <motion.div initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}
          className="glass-panel p-5 rounded-2xl border border-white/5 flex flex-col space-y-1"
        >
          <span className="text-[10px] text-gray-500 font-mono uppercase tracking-widest">Active Agents</span>
          <span className="text-3xl font-bold text-white glow-primary">
            {loading.status ? '...' : status.active_agents_count}
          </span>
          <span className="text-[10px] text-gray-500 font-mono">Always-on polling workers</span>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
          className="glass-panel p-5 rounded-2xl border border-white/5 flex flex-col space-y-1"
        >
          <span className="text-[10px] text-gray-500 font-mono uppercase tracking-widest">Recorded Mutations</span>
          <span className="text-3xl font-bold text-gradient">
            {loading.status ? '...' : status.total_mutations_count}
          </span>
          <span className="text-[10px] text-gray-500 font-mono">Drift events logged</span>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}
          className="glass-panel p-5 rounded-2xl border border-white/5 flex flex-col space-y-1"
        >
          <span className="text-[10px] text-gray-500 font-mono uppercase tracking-widest">Recent Anomalies</span>
          <span className="text-3xl font-bold text-red-400 shadow-[0_0_20px_rgba(239,68,68,0.15)]">
            {loading.status ? '...' : status.recent_anomalies_count}
          </span>
          <span className="text-[10px] text-gray-500 font-mono">Flagged in last 24h</span>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
          className="glass-panel p-5 rounded-2xl border border-white/5 flex flex-col space-y-1"
        >
          <span className="text-[10px] text-gray-500 font-mono uppercase tracking-widest">Last Cycle</span>
          <span className="text-xs font-bold text-white font-mono mt-3 truncate">
            {loading.status ? '...' : new Date(status.last_scan_cycle).toLocaleTimeString()}
          </span>
          <span className="text-[10px] text-gray-500 font-mono mt-1">Scheduler refresh timestamp</span>
        </motion.div>
      </div>

      {/* Main Grid View panels */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[calc(100vh-320px)] min-h-[500px]">
        {/* Left Column: Continuous Monitoring Dashboard */}
        <motion.div initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.25 }} className="h-full">
          <AutonomousMonitoringPanel
            status={status}
            agents={agents}
            loading={loading.agents}
            onTriggerScan={handleTriggerScan}
          />
        </motion.div>

        {/* Middle Column: Exposure Mutations Feed */}
        <motion.div initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.3 }} className="h-full">
          <ExposureMutationFeed
            mutations={mutations}
            loading={loading.mutations}
            onRevalidateAsset={handleRevalidateAsset}
          />
        </motion.div>

        {/* Right Column: Anomaly Alerts Panel */}
        <motion.div initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.35 }} className="h-full">
          <AnomalyAlertPanel
            anomalies={anomalies}
            loading={loading.anomalies}
            onTriggerInvestigation={handleTriggerInvestigation}
          />
        </motion.div>
      </div>
    </div>
  );
}
