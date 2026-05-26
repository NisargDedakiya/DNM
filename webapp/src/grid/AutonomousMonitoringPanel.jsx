import React from 'react';

export default function AutonomousMonitoringPanel({ status, agents, loading, onTriggerScan }) {
  const getHealthBadge = (health) => {
    switch (health?.toLowerCase()) {
      case 'healthy':
        return 'bg-green-500/10 text-green-400 border-green-500/20';
      case 'degraded':
        return 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20';
      default:
        return 'bg-red-500/10 text-red-400 border-red-500/20';
    }
  };

  const getAgentStatusDot = (status) => {
    switch (status?.toLowerCase()) {
      case 'active':
        return 'bg-green-400 shadow-[0_0_8px_rgba(74,222,128,0.8)]';
      case 'idle':
        return 'bg-blue-400 shadow-[0_0_8px_rgba(96,165,250,0.8)]';
      default:
        return 'bg-gray-500';
    }
  };

  return (
    <div className="glass-panel p-6 rounded-2xl border border-white/5 flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between mb-6 shrink-0">
        <div className="flex items-center space-x-2">
          <svg className="w-5 h-5 text-secondary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
          </svg>
          <h3 className="text-base font-bold text-white tracking-wide">Continuous Orchestrator</h3>
        </div>

        <button
          onClick={onTriggerScan}
          className="text-xs font-bold text-white bg-gradient-to-r from-primary to-secondary hover:brightness-110 shadow-[0_0_12px_rgba(0,184,255,0.25)] hover:shadow-[0_0_18px_rgba(0,184,255,0.4)] rounded-lg px-4 py-1.5 transition-all duration-300 flex items-center space-x-1.5"
        >
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span>Trigger Scan</span>
        </button>
      </div>

      {/* Scheduler Metrics */}
      <div className="grid grid-cols-2 gap-4 mb-6 shrink-0">
        <div className="bg-white/[0.01] border border-white/5 p-4 rounded-xl flex flex-col space-y-1.5">
          <span className="text-[10px] text-gray-500 font-mono uppercase tracking-widest">Orchestrator Health</span>
          <div className="flex items-center space-x-2">
            <span className={`text-xs font-bold px-2 py-0.5 rounded border uppercase ${getHealthBadge(status?.grid_health)}`}>
              {status?.grid_health || 'nominal'}
            </span>
          </div>
        </div>

        <div className="bg-white/[0.01] border border-white/5 p-4 rounded-xl flex flex-col space-y-1.5">
          <span className="text-[10px] text-gray-500 font-mono uppercase tracking-widest">Grid Alert Load</span>
          <div className="flex items-center space-x-2">
            <span className={`text-xs font-bold px-2 py-0.5 rounded border uppercase ${status?.grid_status === 'nominal' ? 'text-green-400 border-green-500/20 bg-green-500/5' : 'text-yellow-400 border-yellow-500/20 bg-yellow-500/5'}`}>
              {status?.grid_status || 'nominal'}
            </span>
          </div>
        </div>
      </div>

      {/* Agents Heartbeats */}
      <div className="flex-1 overflow-y-auto space-y-4 pr-1 custom-scrollbar">
        <div>
          <h4 className="text-[10px] font-bold text-gray-600 uppercase tracking-widest mb-3">Distributed Grid Agents</h4>
          {loading ? (
            <div className="flex justify-center py-6">
              <div className="w-5 h-5 border-2 border-primary/20 border-t-primary rounded-full animate-spin"></div>
            </div>
          ) : agents.length === 0 ? (
            <div className="bg-white/[0.01] border border-white/5 p-4 rounded-xl text-center text-xs text-gray-500 font-light">
              No grid monitoring agents registered. Trigger a scan cycle to deploy agents.
            </div>
          ) : (
            <div className="space-y-2.5">
              {agents.map((agent, idx) => (
                <div
                  key={agent.id || idx}
                  className="bg-white/[0.01] border border-white/5 hover:border-white/10 p-3.5 rounded-xl flex items-center justify-between transition-all duration-300"
                >
                  <div className="flex items-center space-x-3">
                    {/* Status beacon */}
                    <div className={`w-2.5 h-2.5 rounded-full ${getAgentStatusDot(agent.status)}`}></div>
                    <div className="flex flex-col">
                      <span className="text-xs font-bold text-white font-mono">
                        Agent-{agent.id?.substring(0, 8) || 'node'}
                      </span>
                      <span className="text-[9px] text-gray-500 font-mono mt-0.5">
                        Monitored assets: {agent.monitored_assets_count || 0}
                      </span>
                    </div>
                  </div>

                  <div className="flex flex-col items-end space-y-0.5 font-mono text-[9px] text-gray-500">
                    <span className="text-gray-400 uppercase tracking-wider font-bold">
                      {agent.status}
                    </span>
                    <span>
                      Heartbeat: {agent.last_heartbeat ? new Date(agent.last_heartbeat).toLocaleTimeString() : 'N/A'}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Adaptive Scan Rules Info */}
        <div className="bg-primary/5 border border-primary/10 rounded-xl p-4 mt-2 shrink-0">
          <div className="flex items-start space-x-3">
            <svg className="w-4 h-4 text-primary mt-0.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div className="space-y-1">
              <h5 className="text-xs font-bold text-white leading-none">Adaptive Polling Active</h5>
              <p className="text-[10px] text-gray-400 leading-normal">
                Continuous Scheduler adapts check rates automatically: volatile assets (mutations in last 7 days) are scanned up to 4x faster, while inactive nodes cool down to minimize targets load.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
