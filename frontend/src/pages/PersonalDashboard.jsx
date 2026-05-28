/**
 * PersonalDashboard Page
 * Main hunting workspace with realtime updates, findings, and active hunts
 */

import React, { useState, useEffect } from 'react';
import { useAuthStore } from '../state/auth';
import huntApi from '../services/huntApi';
import websocket from '../realtime/websocketManager'; // Point to new manager
import WorkingStatus from '../components/WorkingStatus';
import VulnerabilitySection from '../components/VulnerabilitySection';
import ManualCheck from '../components/ManualCheck';
import ReportGeneration from '../components/ReportGeneration';

const PersonalDashboard = () => {
  const { user, activeOrgId } = useAuthStore();
  const organization = { id: activeOrgId || '' };
  const [activeHunts, setActiveHunts] = useState([]);
  const [criticalFindings, setCriticalFindings] = useState([]);
  const [selectedHunt, setSelectedHunt] = useState(null);
  const [selectedFinding, setSelectedFinding] = useState(null);
  const [showManualCheck, setShowManualCheck] = useState(false);
  const [showReportGen, setShowReportGen] = useState(false);
  const [metrics, setMetrics] = useState(null);
  const [highRiskAssets, setHighRiskAssets] = useState([]);
  const [reconFeed, setReconFeed] = useState([]);
  const [aiRecommendations, setAiRecommendations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [connectionStatus, setConnectionStatus] = useState('connecting');
  const [wsError, setWsError] = useState(null);

  // Centralized websocket manages connection automatically
  useEffect(() => {
    setConnectionStatus(websocket.getStatus().isConnected ? 'connected' : 'disconnected');
  }, [websocket.getStatus().isConnected]);

  // Load dashboard data
  useEffect(() => {
    if (!organization?.id) return;

    const loadData = async () => {
      setLoading(true);
      try {
        const [hunts, findings, dashMetrics, riskAssets, aiRecs] = await Promise.all([
          huntApi.getActiveHunts(organization.id),
          huntApi.getCriticalFindings(organization.id),
          huntApi.getDashboardMetrics(organization.id),
          huntApi.getHighRiskAssets(organization.id),
          huntApi.getAIRecommendations(organization.id),
        ]);

        setActiveHunts(hunts);
        setCriticalFindings(findings);
        setMetrics(dashMetrics);
        setHighRiskAssets(riskAssets);
        setAiRecommendations(aiRecs);

        if (hunts.length > 0 && !selectedHunt) {
          setSelectedHunt(hunts[0]);
        }
      } catch (err) {
        console.error('Failed to load dashboard data:', err);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [organization?.id]);

  // Subscribe to recon feed
  useEffect(() => {
    if (!websocket.getStatus().isConnected) return;

    const unsubscribe = websocket.onReconFeed((data) => {
      setReconFeed((prev) => [data, ...prev.slice(0, 19)]);
    });

    return unsubscribe;
  }, []);

  // Load recon feed on mount
  useEffect(() => {
    if (!organization?.id) return;

    const loadReconFeed = async () => {
      try {
        const feed = await huntApi.getReconFeed(organization.id, { limit: 20 });
        setReconFeed(feed);
      } catch (err) {
        console.error('Failed to load recon feed:', err);
      }
    };

    loadReconFeed();
  }, [organization?.id]);

  // Handle finding selection
  const handleSelectFinding = (finding) => {
    setSelectedFinding(finding);
  };

  // Get dashboard status colors
  const getStatusColor = (status) => {
    switch (status?.toLowerCase()) {
      case 'running':
        return 'bg-green-900/40 text-green-300 border-green-500/30';
      case 'paused':
        return 'bg-yellow-900/40 text-yellow-300 border-yellow-500/30';
      case 'completed':
        return 'bg-blue-900/40 text-blue-300 border-blue-500/30';
      case 'failed':
        return 'bg-red-900/40 text-red-300 border-red-500/30';
      default:
        return 'bg-slate-900/40 text-slate-300 border-slate-500/30';
    }
  };

  if (!organization?.id) {
    return (
      <div className="flex items-center justify-center h-screen bg-slate-950">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-cyan-400 mb-2">No Organization</h1>
          <p className="text-slate-400">Please select an organization to continue</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-300 p-4 md:p-6">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-3xl font-bold text-cyan-400 flex items-center gap-2">
              <span>🎯 Hunting Workspace</span>
              {connectionStatus === 'connected' && (
                <span className="text-xs bg-green-900/40 text-green-300 border border-green-500/30 px-2 py-1 rounded">
                  Live
                </span>
              )}
              {connectionStatus === 'connecting' && (
                <span className="text-xs bg-yellow-900/40 text-yellow-300 border border-yellow-500/30 px-2 py-1 rounded">
                  Connecting...
                </span>
              )}
              {connectionStatus === 'disconnected' && (
                <span className="text-xs bg-red-900/40 text-red-300 border border-red-500/30 px-2 py-1 rounded">
                  Offline
                </span>
              )}
            </h1>
            <p className="text-slate-400 mt-1">
              {organization?.name || 'Organization'} · {user?.email}
            </p>
          </div>

          {wsError && (
            <div className="bg-red-900/20 border border-red-500/30 px-3 py-1.5 rounded text-xs text-red-300">
              Connection error: {wsError}
            </div>
          )}
        </div>

        {/* Quick stats */}
        {metrics && (
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <div className="bg-slate-900/50 border border-slate-700 rounded px-3 py-2">
              <p className="text-xs text-slate-500 mb-1">Active Hunts</p>
              <p className="text-lg font-bold text-cyan-400">
                {metrics.active_hunts || activeHunts.length}
              </p>
            </div>

            <div className="bg-slate-900/50 border border-slate-700 rounded px-3 py-2">
              <p className="text-xs text-slate-500 mb-1">Critical Findings</p>
              <p className="text-lg font-bold text-red-400">{metrics.critical_findings || 0}</p>
            </div>

            <div className="bg-slate-900/50 border border-slate-700 rounded px-3 py-2">
              <p className="text-xs text-slate-500 mb-1">Pending Verification</p>
              <p className="text-lg font-bold text-yellow-400">{metrics.pending_verification || 0}</p>
            </div>

            <div className="bg-slate-900/50 border border-slate-700 rounded px-3 py-2">
              <p className="text-xs text-slate-500 mb-1">Submitted Reports</p>
              <p className="text-lg font-bold text-green-400">{metrics.submitted_reports || 0}</p>
            </div>

            <div className="bg-slate-900/50 border border-slate-700 rounded px-3 py-2">
              <p className="text-xs text-slate-500 mb-1">Month's Bounty</p>
              <p className="text-lg font-bold text-blue-400">${metrics.monthly_bounty || 0}</p>
            </div>
          </div>
        )}
      </div>

      {/* Main content grid */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 mb-6">
        {/* Left column: Active hunts + Working status */}
        <div className="xl:col-span-1 space-y-6">
          {/* Active hunts */}
          <div className="bg-slate-950 border border-cyan-500/20 rounded-lg overflow-hidden">
            <div className="border-b border-cyan-500/20 bg-slate-900/50 px-4 py-3">
              <h2 className="text-sm font-semibold text-cyan-400 uppercase tracking-wider">
                Active Hunts
              </h2>
            </div>

            <div className="max-h-64 overflow-y-auto p-3 space-y-2">
              {activeHunts.map((hunt) => (
                <div
                  key={hunt.id}
                  onClick={() => setSelectedHunt(hunt)}
                  className={`p-3 rounded border cursor-pointer transition-all ${
                    selectedHunt?.id === hunt.id
                      ? 'border-cyan-500 bg-cyan-900/20'
                      : 'border-slate-700 bg-slate-900/30 hover:border-cyan-500/50'
                  }`}
                >
                  <div className="flex items-start justify-between mb-2">
                    <h3 className="text-sm font-semibold text-cyan-300 truncate">{hunt.name}</h3>
                    <span className={`text-xs px-2 py-0.5 rounded border ${getStatusColor(hunt.status)}`}>
                      {hunt.status?.toUpperCase()}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500">{hunt.target || 'No target'}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Working status */}
          {selectedHunt && (
            <WorkingStatus huntId={selectedHunt.id} organizationId={organization.id} />
          )}
        </div>

        {/* Middle column: Vulnerability section */}
        <div className="xl:col-span-1">
          <VulnerabilitySection
            organizationId={organization.id}
            onSelectFinding={handleSelectFinding}
          />
        </div>

        {/* Right column: High-risk assets + Recommendations */}
        <div className="xl:col-span-1 space-y-6">
          {/* High-risk assets */}
          <div className="bg-slate-950 border border-cyan-500/20 rounded-lg overflow-hidden">
            <div className="border-b border-cyan-500/20 bg-slate-900/50 px-4 py-3">
              <h2 className="text-sm font-semibold text-cyan-400 uppercase tracking-wider">
                High-Risk Assets
              </h2>
            </div>

            <div className="max-h-64 overflow-y-auto p-3 space-y-2">
              {highRiskAssets.map((asset) => (
                <div
                  key={asset.id}
                  className="p-3 bg-slate-900/30 border border-red-500/20 rounded hover:border-red-500/40 transition-colors"
                >
                  <h3 className="text-sm font-semibold text-red-300 truncate">{asset.name}</h3>
                  <p className="text-xs text-slate-500 mt-1">{asset.description || 'Asset'}</p>
                  <div className="text-xs text-red-400 font-mono mt-2">
                    Risk Score: {asset.risk_score || 0}/100
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* AI Recommendations */}
          <div className="bg-slate-950 border border-cyan-500/20 rounded-lg overflow-hidden">
            <div className="border-b border-cyan-500/20 bg-slate-900/50 px-4 py-3">
              <h2 className="text-sm font-semibold text-purple-400 uppercase tracking-wider">
                AI Recommendations
              </h2>
            </div>

            <div className="max-h-48 overflow-y-auto p-3 space-y-2">
              {aiRecommendations.map((rec, idx) => (
                <div
                  key={idx}
                  className="p-3 bg-purple-900/20 border border-purple-500/20 rounded"
                >
                  <p className="text-sm text-purple-300">{rec.recommendation}</p>
                  <p className="text-xs text-slate-500 mt-1">Priority: {rec.priority}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Recon feed */}
      <div className="bg-slate-950 border border-cyan-500/20 rounded-lg overflow-hidden">
        <div className="border-b border-cyan-500/20 bg-slate-900/50 px-4 py-3">
          <h2 className="text-sm font-semibold text-cyan-400 uppercase tracking-wider">
            Realtime Recon Feed
          </h2>
        </div>

        <div className="max-h-48 overflow-y-auto">
          {reconFeed.length === 0 ? (
            <div className="p-6 text-center text-slate-500">
              <p className="text-sm">Waiting for recon events...</p>
            </div>
          ) : (
            <div className="divide-y divide-slate-700">
              {reconFeed.map((event, idx) => (
                <div key={idx} className="px-4 py-3 hover:bg-slate-900/50 transition-colors">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-cyan-300">{event.message}</p>
                      <p className="text-xs text-slate-500 mt-1">
                        {new Date(event.timestamp).toLocaleTimeString()}
                      </p>
                    </div>
                    {event.severity && (
                      <span className="text-xs px-2 py-1 rounded-full bg-yellow-900/40 text-yellow-300 whitespace-nowrap">
                        {event.severity}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Selected finding details panel */}
      {selectedFinding && (
        <div className="fixed bottom-6 right-6 bg-slate-950 border border-cyan-500/30 rounded-lg p-4 max-w-sm shadow-lg">
          <div className="flex items-start justify-between mb-3">
            <h3 className="text-sm font-semibold text-cyan-400 line-clamp-2">
              {selectedFinding.title}
            </h3>
            <button
              onClick={() => setSelectedFinding(null)}
              className="text-slate-500 hover:text-slate-300"
            >
              ✕
            </button>
          </div>

          <div className="space-y-2 mb-4">
            <div className="flex justify-between text-xs">
              <span className="text-slate-500">Severity:</span>
              <span className="text-cyan-300 font-mono uppercase">
                {selectedFinding.severity}
              </span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-slate-500">Status:</span>
              <span className="text-green-300 font-mono uppercase">
                {selectedFinding.status}
              </span>
            </div>
          </div>

          <div className="flex gap-2">
            <button
              onClick={() => {
                setShowManualCheck(true);
              }}
              className="flex-1 px-3 py-1.5 bg-cyan-600 rounded text-xs text-white hover:bg-cyan-500 transition-colors"
            >
              Verify
            </button>

            <button
              onClick={() => {
                setShowReportGen(true);
              }}
              className="flex-1 px-3 py-1.5 bg-green-600 rounded text-xs text-white hover:bg-green-500 transition-colors"
            >
              Report
            </button>
          </div>
        </div>
      )}

      {/* Modals */}
      {showManualCheck && selectedFinding && (
        <ManualCheck
          finding={selectedFinding}
          onClose={() => setShowManualCheck(false)}
          onVerified={(findingId) => {
            setShowManualCheck(false);
            setSelectedFinding(null);
          }}
        />
      )}

      {showReportGen && selectedFinding && (
        <ReportGeneration
          finding={selectedFinding}
          onClose={() => setShowReportGen(false)}
          onSubmit={(findingId) => {
            setShowReportGen(false);
            setSelectedFinding(null);
          }}
        />
      )}
    </div>
  );
};

export default PersonalDashboard;
