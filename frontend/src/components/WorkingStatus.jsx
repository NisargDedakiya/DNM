/**
 * WorkingStatus Component
 * Terminal-style interface for realtime hunting operations
 * Shows scanner stage, progress, and live event feed
 */

import React, { useState, useEffect, useRef } from 'react';
import websocket from '../services/websocket';

const WorkingStatus = ({ huntId, organizationId }) => {
  const [logs, setLogs] = useState([]);
  const [currentStage, setCurrentStage] = useState('idle');
  const [progress, setProgress] = useState(0);
  const [severity, setSeverity] = useState('info');
  const [isRunning, setIsRunning] = useState(false);
  const logsEndRef = useRef(null);

  // Auto-scroll to bottom
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  // Subscribe to hunt progress updates
  useEffect(() => {
    if (!huntId || !websocket.getStatus().isConnected) return;

    const unsubscribe = websocket.onHuntProgress((data) => {
      if (data.hunt_id !== huntId) return;

      // Add log entry
      const timestamp = new Date().toLocaleTimeString('en-US', {
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });

      const logEntry = {
        id: `${Date.now()}-${Math.random()}`,
        timestamp,
        message: data.message || 'Stage update',
        stage: data.stage || currentStage,
        severity: data.severity || 'info',
      };

      setLogs((prev) => [...prev.slice(-99), logEntry]); // Keep last 100 logs
      setCurrentStage(data.stage || currentStage);
      setProgress(data.progress || 0);
      setSeverity(data.severity || 'info');
      setIsRunning(data.status === 'running');
    });

    return unsubscribe;
  }, [huntId]);

  // Add initial log
  useEffect(() => {
    if (logs.length === 0 && huntId) {
      const timestamp = new Date().toLocaleTimeString('en-US', {
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });

      setLogs([
        {
          id: 'init',
          timestamp,
          message: `Initialized working status for hunt ${huntId}`,
          stage: 'initialized',
          severity: 'info',
        },
      ]);
    }
  }, [huntId]);

  // Determine severity color
  const getSeverityColor = (sev) => {
    switch (sev) {
      case 'critical':
        return 'text-red-500';
      case 'error':
        return 'text-red-400';
      case 'warning':
        return 'text-yellow-500';
      case 'success':
        return 'text-green-500';
      default:
        return 'text-cyan-400';
    }
  };

  // Determine stage color
  const getStageColor = (stage) => {
    switch (stage) {
      case 'reconnaissance':
        return 'bg-blue-900/30 border-blue-500/50';
      case 'scanning':
        return 'bg-cyan-900/30 border-cyan-500/50';
      case 'analysis':
        return 'bg-purple-900/30 border-purple-500/50';
      case 'triage':
        return 'bg-amber-900/30 border-amber-500/50';
      case 'completed':
        return 'bg-green-900/30 border-green-500/50';
      case 'error':
        return 'bg-red-900/30 border-red-500/50';
      default:
        return 'bg-slate-900/30 border-slate-500/50';
    }
  };

  return (
    <div className="h-full flex flex-col bg-slate-950 border border-cyan-500/20 rounded-lg overflow-hidden">
      {/* Header */}
      <div className="border-b border-cyan-500/20 bg-slate-900/50 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex flex-col">
            <span className="text-xs text-cyan-500 font-mono uppercase tracking-wider">
              HUNT STATUS
            </span>
            <span className="text-sm text-cyan-400 font-mono">
              {huntId ? `Hunt: ${huntId.slice(0, 8)}...` : 'No hunt selected'}
            </span>
          </div>
        </div>

        {/* Running indicator */}
        {isRunning && (
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
            <span className="text-xs text-green-400 font-mono uppercase tracking-wider">
              ACTIVE
            </span>
          </div>
        )}
      </div>

      {/* Stage indicator */}
      <div className={`px-4 py-2 border-b border-cyan-500/20 ${getStageColor(currentStage)}`}>
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-cyan-400 font-mono uppercase tracking-wider">
            Current Stage
          </span>
          <span className="text-xs font-mono uppercase text-cyan-300">
            {currentStage}
          </span>
        </div>

        {/* Progress bar */}
        <div className="w-full bg-slate-900/50 rounded h-1 border border-cyan-500/20 overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-cyan-500 to-blue-500 transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>
        <div className="text-right mt-1">
          <span className="text-xs text-cyan-400 font-mono">{Math.round(progress)}%</span>
        </div>
      </div>

      {/* Terminal logs */}
      <div className="flex-1 overflow-y-auto bg-slate-950 font-mono text-sm p-3 space-y-1">
        {logs.length === 0 ? (
          <div className="text-slate-500 text-xs">
            [<span className="text-cyan-400">*</span>] Waiting for events...
          </div>
        ) : (
          logs.map((log) => (
            <div
              key={log.id}
              className="text-xs leading-relaxed hover:bg-slate-900/30 px-1 py-0.5 rounded transition-colors"
            >
              <span className="text-slate-600">[{log.timestamp}]</span>
              {' '}
              <span className={getSeverityColor(log.severity)}>
                {log.severity.toUpperCase()}
              </span>
              {' '}
              <span className="text-slate-400">→</span>
              {' '}
              <span className="text-cyan-300">{log.message}</span>
            </div>
          ))
        )}
        <div ref={logsEndRef} />
      </div>

      {/* Footer stats */}
      <div className="border-t border-cyan-500/20 bg-slate-900/50 px-4 py-2 grid grid-cols-4 gap-2 text-xs">
        <div>
          <span className="text-slate-500">Logs:</span>
          <span className="text-cyan-400 font-mono ml-1">{logs.length}</span>
        </div>
        <div>
          <span className="text-slate-500">Progress:</span>
          <span className="text-cyan-400 font-mono ml-1">{Math.round(progress)}%</span>
        </div>
        <div>
          <span className="text-slate-500">Status:</span>
          <span className={`font-mono ml-1 ${isRunning ? 'text-green-400' : 'text-slate-500'}`}>
            {isRunning ? 'RUNNING' : 'IDLE'}
          </span>
        </div>
        <div>
          <span className="text-slate-500">Stage:</span>
          <span className="text-cyan-400 font-mono ml-1">
            {currentStage.toUpperCase().slice(0, 4)}
          </span>
        </div>
      </div>
    </div>
  );
};

export default WorkingStatus;
