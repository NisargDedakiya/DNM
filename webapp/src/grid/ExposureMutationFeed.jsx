import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';

export default function ExposureMutationFeed({ mutations, loading, onRevalidateAsset }) {
  const getSeverityBadge = (severity) => {
    switch (severity?.toLowerCase()) {
      case 'critical':
        return 'bg-red-500/20 text-red-400 border-red-500/30';
      case 'high':
        return 'bg-orange-500/20 text-orange-400 border-orange-500/30';
      case 'medium':
        return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
      case 'low':
        return 'bg-green-500/20 text-green-400 border-green-500/30';
      default:
        return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
    }
  };

  const getMutationIcon = (type) => {
    switch (type) {
      case 'dns_drift':
        return (
          <svg className="w-4 h-4 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v1m6 11h2m-6 0h-2v4m0-11v3m0 0h.01M12 12h4.01M16 20h4M4 12h4m12 0a8 8 0 11-16 0 8 8 0 0116 0z" />
          </svg>
        );
      case 'cloud_exposure':
        return (
          <svg className="w-4 h-4 text-orange-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z" />
          </svg>
        );
      case 'auth_mutation':
        return (
          <svg className="w-4 h-4 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
          </svg>
        );
      default:
        return (
          <svg className="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
    }
  };

  return (
    <div className="glass-panel p-6 rounded-2xl border border-white/5 flex flex-col h-full overflow-hidden">
      <div className="flex items-center justify-between mb-5 shrink-0">
        <div className="flex items-center space-x-2">
          <svg className="w-5 h-5 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 1121.21 8H18.2" />
          </svg>
          <h3 className="text-base font-bold text-white tracking-wide">Exposure Mutation Feed</h3>
        </div>
        <div className="w-2.5 h-2.5 rounded-full bg-green-500 animate-ping"></div>
      </div>

      <div className="flex-1 overflow-y-auto space-y-4 pr-1 custom-scrollbar">
        {loading ? (
          <div className="flex flex-col items-center justify-center py-16 space-y-3">
            <div className="w-6 h-6 border-2 border-primary/20 border-t-primary rounded-full animate-spin"></div>
            <span className="text-xs text-gray-500 font-mono">Syncing mutation feed...</span>
          </div>
        ) : mutations.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <svg className="w-8 h-8 text-gray-600 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
            <span className="text-xs text-gray-400 font-medium">No mutations recorded</span>
            <span className="text-[10px] text-gray-500 mt-1">Attack surface mutations will appear here.</span>
          </div>
        ) : (
          <div className="relative border-l border-white/5 pl-4 ml-2 space-y-6 py-2">
            <AnimatePresence initial={false}>
              {mutations.map((mutation, idx) => (
                <motion.div
                  key={mutation.id || idx}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  className="relative group"
                >
                  {/* Timeline bullet */}
                  <div className="absolute -left-[25px] top-1 w-4.5 h-4.5 rounded-full bg-slate-900 border border-white/10 flex items-center justify-center shadow-[0_0_10px_rgba(0,184,255,0.05)] group-hover:border-primary/50 group-hover:shadow-[0_0_12px_rgba(0,184,255,0.2)] transition-all duration-300">
                    {getMutationIcon(mutation.mutation_type)}
                  </div>

                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <span className="text-xs font-bold text-white truncate max-w-[150px] group-hover:text-primary transition-colors duration-300">
                          {mutation.asset?.hostname || 'unknown'}
                        </span>
                        <span className="text-[9px] text-gray-500 font-mono">
                          ({mutation.asset?.ip_address || 'No IP'})
                        </span>
                      </div>
                      <span className={`text-[8px] font-mono uppercase px-1.5 py-0.5 rounded border ${getSeverityBadge(mutation.severity)}`}>
                        {mutation.severity}
                      </span>
                    </div>

                    <div className="bg-white/[0.01] border border-white/5 p-3 rounded-lg flex flex-col space-y-2 group-hover:border-white/10 group-hover:bg-white/[0.02] transition-all duration-300">
                      <div className="flex items-center justify-between shrink-0">
                        <span className="text-[10px] font-mono text-gray-400 capitalize">
                          {mutation.mutation_type?.replace('_', ' ')}
                        </span>
                        <span className="text-[9px] font-mono text-gray-600">
                          {mutation.created_at ? new Date(mutation.created_at).toLocaleTimeString() : 'Recent'}
                        </span>
                      </div>
                      
                      <p className="text-xs text-gray-300 leading-relaxed font-light">
                        {mutation.summary}
                      </p>

                      <div className="flex justify-end pt-1 border-t border-white/5 shrink-0">
                        <button
                          onClick={() => onRevalidateAsset && onRevalidateAsset(mutation.asset?.id)}
                          className="text-[9px] font-bold text-gray-400 hover:text-white hover:bg-white/10 border border-white/10 hover:border-white/20 rounded px-2 py-0.5 transition-all duration-300 flex items-center space-x-1"
                        >
                          <svg className="w-2.5 h-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M4 4v5h.582m15.356 2A8.001 8.001 0 1121.21 8H18.2" />
                          </svg>
                          <span>Re-check</span>
                        </button>
                      </div>
                    </div>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        )}
      </div>
    </div>
  );
}
