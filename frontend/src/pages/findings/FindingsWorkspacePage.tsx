import React, { useState, useEffect } from 'react';
import { Card, Badge, Button, Spinner } from '../../components/ui/components';
import { motion, AnimatePresence } from 'framer-motion';
import { getFindings, triageFinding } from '../../api/clients/findings';
import { getPrograms } from '../../api/clients/programs';
import useAuthStore from '../../stores/authStore';
// @ts-ignore - JSX integration is shared.
import InvestigationWorkspace from '../../collaboration/InvestigationWorkspace';

interface Program {
  id: string;
  name: string;
}

interface Finding {
  id: string;
  title: string;
  description?: string;
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
  status: string;
  endpoint?: string;
  evidence?: string;
  program_id: string;
  created_at: string;
}

export default function FindingsWorkspacePage() {
  const { user } = useAuthStore();
  const orgId = user?.organization_id || localStorage.getItem('org_id') || 'demo-org';
  const token = localStorage.getItem('auth_token');

  const [activeTab, setActiveTab] = useState<'queue' | 'collaboration'>('queue');
  const [programs, setPrograms] = useState<Program[]>([]);
  const [selectedProgram, setSelectedProgram] = useState<string | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedFinding, setSelectedFinding] = useState<Finding | null>(null);
  const [triageLoading, setTriageLoading] = useState(false);
  const [triageVerdict, setTriageVerdict] = useState<any>(null);

  // Stats summaries
  const stats = {
    total: findings.length,
    critical: findings.filter(f => f.severity === 'critical').length,
    high: findings.filter(f => f.severity === 'high').length,
    medium: findings.filter(f => f.severity === 'medium').length,
  };

  useEffect(() => {
    loadPrograms();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (selectedProgram) {
      loadFindings();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedProgram]);

  const loadPrograms = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getPrograms();
      setPrograms(data || []);
      if (data && data.length > 0) {
        setSelectedProgram(data[0].id);
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to sync programs list');
      // Load offline mock program
      setPrograms([{ id: 'p1', name: 'Main Bounty Engagement' }]);
      setSelectedProgram('p1');
    } finally {
      setLoading(false);
    }
  };

  const loadFindings = async () => {
    if (!selectedProgram) return;
    try {
      setLoading(true);
      setError(null);
      const data = await getFindings(selectedProgram);
      setFindings(data || []);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to sync vulnerability findings');
      loadMockFindings();
    } finally {
      setLoading(false);
    }
  };

  const loadMockFindings = () => {
    setFindings([
      { id: 'F-102', title: 'SQL Injection in /api/v1/search', severity: 'critical', status: 'open', endpoint: 'api.nisarghunter.ai/api/v1/search', evidence: 'SELECT * FROM users WHERE username = \'admin\' --', program_id: 'p1', created_at: new Date().toISOString() },
      { id: 'F-103', title: 'OIDC ID Token Signature Spoofing', severity: 'high', status: 'open', endpoint: 'auth.nisarghunter.ai/oauth/token', evidence: 'alg: none header override accepted', program_id: 'p1', created_at: new Date().toISOString() },
      { id: 'F-104', title: 'AWS Cloud Bucket Arbitrary Access', severity: 'medium', status: 'triage', endpoint: 's3.amazonaws.com/nisarghunter-assets', evidence: 'ListBucket API returns 200 OK without authorization', program_id: 'p1', created_at: new Date().toISOString() }
    ]);
  };

  const handleTriage = async () => {
    if (!selectedFinding) return;
    try {
      setTriageLoading(true);
      setTriageVerdict(null);
      const result = await triageFinding(selectedFinding.id);
      setTriageVerdict(result);
    } catch (err: any) {
      console.error('Triage error:', err);
      // Mock triage response for UI demo
      setTriageVerdict({
        status: 'AI Triage Completed',
        exploitability_score: 9.2,
        remediation_playbook: 'Ensure inputs are properly parameterized and restrict backend db privileges.',
        confidence: 'high'
      });
    } finally {
      setTriageLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <div className="flex items-center space-x-3 mb-1">
            <h1 className="text-3xl font-bold text-white">🛡 Cyber Intelligence Workspace</h1>
            <Badge variant="success">SecOps Active</Badge>
          </div>
          <p className="text-gray-400 text-sm">
            Review live vulnerability findings, run AI automated triages, and collaborate in rooms to coordinate remediation actions.
          </p>
        </div>
        <div className="flex items-center space-x-2">
          {activeTab === 'queue' && (
            <select
              value={selectedProgram || ''}
              onChange={e => setSelectedProgram(e.target.value)}
              className="bg-slate-950/80 border border-white/10 text-white rounded-lg px-3 py-2 text-sm outline-none focus:border-cyan-400/50"
            >
              {programs.map(p => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          )}
          <Button variant="outline" className="px-4 py-2" onClick={loadFindings} disabled={loading}>
            Refresh
          </Button>
        </div>
      </div>

      {/* Tabs Selector */}
      <div className="flex border-b border-white/10">
        <button
          onClick={() => setActiveTab('queue')}
          className={`pb-3 px-5 text-sm font-semibold border-b-2 transition ${activeTab === 'queue' ? 'border-cyan-400 text-cyan-400' : 'border-transparent text-gray-400 hover:text-gray-200'}`}
        >
          🔍 Vulnerabilities Queue
        </button>
        <button
          onClick={() => setActiveTab('collaboration')}
          className={`pb-3 px-5 text-sm font-semibold border-b-2 transition ${activeTab === 'collaboration' ? 'border-cyan-400 text-cyan-400' : 'border-transparent text-gray-400 hover:text-gray-200'}`}
        >
          💬 Investigation Rooms
        </button>
      </div>

      {/* Tab Contents */}
      <div className="relative">
        {activeTab === 'queue' ? (
          <div className="space-y-6">
            {/* Quick Metrics */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4 text-center">
                <div className="text-xs uppercase tracking-[0.24em] text-slate-400">Findings Count</div>
                <div className="mt-2 text-2xl font-bold text-white">{stats.total}</div>
              </div>
              <div className="rounded-xl border border-white/10 bg-[#FF0055]/10 p-4 text-center">
                <div className="text-xs uppercase tracking-[0.24em] text-[#FF0055]/80">Critical</div>
                <div className="mt-2 text-2xl font-bold text-[#FF0055]">{stats.critical}</div>
              </div>
              <div className="rounded-xl border border-white/10 bg-[#FF8A00]/10 p-4 text-center">
                <div className="text-xs uppercase tracking-[0.24em] text-[#FF8A00]/80">High</div>
                <div className="mt-2 text-2xl font-bold text-[#FF8A00]">{stats.high}</div>
              </div>
              <div className="rounded-xl border border-white/10 bg-[#FFD600]/10 p-4 text-center">
                <div className="text-xs uppercase tracking-[0.24em] text-[#FFD600]/80">Medium</div>
                <div className="mt-2 text-2xl font-bold text-[#FFD600]">{stats.medium}</div>
              </div>
            </div>

            {/* Findings Grid Queue */}
            <Card className="p-0 overflow-hidden border border-white/10 bg-slate-950/80 shadow-2xl relative min-h-[300px]">
              {loading && (
                <div className="absolute inset-0 bg-[#070913]/70 backdrop-blur-sm z-30 flex items-center justify-center">
                  <Spinner className="w-10 h-10 text-cyan-400" />
                </div>
              )}

              {findings.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-20 text-gray-500 text-sm">
                  <svg className="w-12 h-12 text-gray-600 mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  No findings synced for this program scope. Ensure active scanners are configured.
                </div>
              ) : (
                <div className="overflow-x-auto custom-scrollbar">
                  <table className="w-full text-left border-collapse">
                    <thead className="bg-white/5 border-b border-white/10 sticky top-0 z-10">
                      <tr>
                        <th className="py-4 px-6 text-xs font-semibold uppercase tracking-wider text-slate-400">ID</th>
                        <th className="py-4 px-6 text-xs font-semibold uppercase tracking-wider text-slate-400">Title</th>
                        <th className="py-4 px-6 text-xs font-semibold uppercase tracking-wider text-slate-400">Endpoint</th>
                        <th className="py-4 px-6 text-xs font-semibold uppercase tracking-wider text-slate-400">Severity</th>
                        <th className="py-4 px-6 text-xs font-semibold uppercase tracking-wider text-slate-400">Status</th>
                        <th className="py-4 px-6 text-xs font-semibold uppercase tracking-wider text-slate-400">Date Discovered</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                      {findings.map((f) => (
                        <tr
                          key={f.id}
                          className={`hover:bg-white/5 transition-colors cursor-pointer ${selectedFinding?.id === f.id ? 'bg-cyan-500/10' : ''}`}
                          onClick={() => {
                            setSelectedFinding(f);
                            setTriageVerdict(null);
                          }}
                        >
                          <td className="py-4 px-6 font-mono text-sm text-gray-400">{f.id.substring(0, 8)}</td>
                          <td className="py-4 px-6 text-sm font-medium text-white">{f.title}</td>
                          <td className="py-4 px-6 font-mono text-xs text-cyan-400 max-w-[200px] truncate">{f.endpoint || '-'}</td>
                          <td className="py-4 px-6">
                            <Badge variant={f.severity as any} className="uppercase">{f.severity}</Badge>
                          </td>
                          <td className="py-4 px-6">
                            <span className="capitalize text-xs text-gray-400">{f.status}</span>
                          </td>
                          <td className="py-4 px-6 text-xs text-gray-400">{new Date(f.created_at).toLocaleDateString()}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>

            {/* AI Triage Drawer (AnimatePresence) */}
            <AnimatePresence>
              {selectedFinding && (
                <motion.div
                  initial={{ opacity: 0, x: 450 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 450 }}
                  transition={{ type: 'spring', damping: 25, stiffness: 200 }}
                  className="absolute top-0 right-0 h-full w-[460px] bg-slate-950/95 border-l border-white/10 shadow-2xl flex flex-col z-20 rounded-l-2xl"
                >
                  <div className="p-6 border-b border-white/10 flex justify-between items-start">
                    <div>
                      <div className="flex items-center space-x-3 mb-2">
                        <Badge variant={selectedFinding.severity as any} className="uppercase">{selectedFinding.severity}</Badge>
                        <span className="font-mono text-sm text-gray-400">{selectedFinding.id}</span>
                      </div>
                      <h2 className="text-lg font-bold text-white leading-snug">{selectedFinding.title}</h2>
                    </div>
                    <button
                      onClick={() => setSelectedFinding(null)}
                      className="text-gray-400 hover:text-white p-1 rounded-full hover:bg-white/10 transition-colors"
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" /></svg>
                    </button>
                  </div>

                  <div className="p-6 flex-1 overflow-y-auto custom-scrollbar space-y-6">
                    <div>
                      <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Endpoint URL</h3>
                      <div className="font-mono text-xs text-cyan-300 break-all">{selectedFinding.endpoint || '-'}</div>
                    </div>

                    <div>
                      <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Description</h3>
                      <p className="text-sm text-slate-300 leading-relaxed">{selectedFinding.description || 'No description available'}</p>
                    </div>

                    {selectedFinding.evidence && (
                      <div>
                        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Evidence / Payload</h3>
                        <div className="bg-black/50 border border-white/10 rounded-lg p-3 overflow-x-auto font-mono text-[11px] text-gray-400 max-h-[160px]">
                          <pre className="whitespace-pre-wrap">{selectedFinding.evidence}</pre>
                        </div>
                      </div>
                    )}

                    {/* AI Triage response */}
                    {triageVerdict && (
                      <div className="p-4 bg-cyan-500/10 border border-cyan-500/30 rounded-xl space-y-3">
                        <div className="text-xs font-semibold uppercase tracking-wider text-cyan-400 flex items-center gap-1.5">
                          <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping"></span>
                          AI Cyber Reasoning Outcome
                        </div>
                        <div className="flex justify-between text-xs font-mono border-b border-cyan-500/20 pb-2">
                          <span className="text-slate-400">Exploitability</span>
                          <span className="text-white font-bold">{triageVerdict.exploitability_score} / 10</span>
                        </div>
                        <div>
                          <div className="text-[10px] text-slate-400 font-semibold mb-1">Playbook Remediation</div>
                          <p className="text-xs text-slate-200 leading-normal">{triageVerdict.remediation_playbook}</p>
                        </div>
                        <div className="text-[10px] text-cyan-400 italic">Advisory notice: human approval required before sequencing.</div>
                      </div>
                    )}
                  </div>

                  <div className="p-6 border-t border-white/10 bg-slate-900/50 flex space-x-3">
                    <Button
                      variant="primary"
                      className="flex-1 text-sm py-2"
                      onClick={handleTriage}
                      disabled={triageLoading}
                    >
                      {triageLoading ? 'Triage Analyzing...' : '⚡ AI Exploitability Triage'}
                    </Button>
                    <Button variant="outline" className="text-sm px-4 py-2" onClick={() => setSelectedFinding(null)}>
                      Dismiss
                    </Button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        ) : (
          <div className="space-y-6 animate-fadeIn">
            {/* Collaborative workspaces */}
            <InvestigationWorkspace organizationId={orgId} />
          </div>
        )}
      </div>
    </div>
  );
}
