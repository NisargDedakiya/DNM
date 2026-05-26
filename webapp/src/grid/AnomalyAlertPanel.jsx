import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';

export default function AnomalyAlertPanel({ anomalies, loading, onTriggerInvestigation }) {
  const getSeverityStyle = (severity) => {
    switch (severity?.toLowerCase()) {
      case 'critical':
        return 'bg-red-500/10 text-red-400 border-red-500/20 shadow-[0_0_15px_rgba(239,68,68,0.1)]';
      case 'high':
        return 'bg-orange-500/10 text-orange-400 border-orange-500/20 shadow-[0_0_15px_rgba(249,115,22,0.1)]';
      case 'medium':
        return 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20';
      default:
        return 'bg-blue-500/10 text-blue-400 border-blue-500/20';
    }
  };

  return (
    <div className="glass-panel p-6 rounded-2xl border border-white/5 flex flex-col h-full overflow-hidden">
      <div className="flex items-center justify-between mb-5 shrink-0">
        <div className="flex items-center space-x-2">
          <svg className="w-5 h-5 text-red-400 animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <h3 className="text-base font-bold text-white tracking-wide">Autonomous Anomaly Alerts</h3>
        </div>
        <span className="text-[10px] font-mono text-gray-500 bg-white/5 px-2 py-0.5 rounded-full uppercase">Realtime</span>
      </div>

      <div className="flex-1 overflow-y-auto space-y-3 custom-scrollbar pr-1">
        {loading ? (
          <div className="flex flex-col items-center justify-center py-12 space-y-3">
            <div className="w-6 h-6 border-2 border-primary/20 border-t-primary rounded-full animate-spin"></div>
            <span className="text-xs text-gray-500 font-mono">Analyzing baseline distributions...</span>
          </div>
        ) : anomalies.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <div className="w-12 h-12 rounded-xl bg-white/5 flex items-center justify-center mb-3">
              <svg className="w-6 h-6 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <span className="text-xs text-gray-400 font-medium">No Anomalies Detected</span>
            <span className="text-[10px] text-gray-500 mt-1">Grid posture is currently within nominal limits.</span>
          </div>
        ) : (
          <AnimatePresence initial={false}>
            {anomalies.map((anomaly, idx) => (
              <motion.div
                key={anomaly.id || idx}
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className={`p-4 rounded-xl border flex flex-col space-y-3 transition-all duration-300 hover:bg-white/[0.02] ${getSeverityStyle(anomaly.severity)}`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex flex-col">
                    <span className="text-[10px] font-mono uppercase tracking-widest font-bold opacity-80">
                      {anomaly.anomaly_type?.replace('_', ' ')}
                    </span>
                    <span className="text-xs text-white font-medium mt-1 leading-relaxed">
                      {anomaly.summary}
                    </span>
                  </div>
                  <span className={`text-[9px] font-bold uppercase px-2 py-0.5 rounded border border-current ml-2`}>
                    {anomaly.severity}
                  </span>
                </div>

                <div className="flex items-center justify-between border-t border-white/5 pt-3 mt-1 shrink-0">
                  <div className="flex items-center space-x-1.5 text-gray-500 text-[10px] font-mono">
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span>
                      {anomaly.detected_at ? new Date(anomaly.detected_at).toLocaleTimeString() : 'Just now'}
                    </span>
                  </div>

                  <button
                    onClick={() => onTriggerInvestigation && onTriggerInvestigation(anomaly)}
                    className="text-[10px] font-bold text-primary hover:text-white bg-primary/10 hover:bg-primary/30 border border-primary/20 rounded px-2.5 py-1 transition-all duration-300 flex items-center space-x-1"
                  >
                    <span>Investigate</span>
                    <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7" />
                    </svg>
                  </button>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        )}
      </div>
    </div>
  );
}
