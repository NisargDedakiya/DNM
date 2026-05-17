import React, { useState } from 'react';
import { Card, Badge, Button } from '../../components/ui/components';
import { motion, AnimatePresence } from 'framer-motion';
import { generateReconPlan, previewWorkflow, getRecommendations } from '../../api/clients/recon';
import useAuthStore from '../../stores/authStore';

type TabId = 'plan' | 'workflow' | 'recommendations';

const TABS: { id: TabId; label: string; icon: string }[] = [
  { id: 'plan', label: 'AI Recon Plan', icon: 'M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z' },
  { id: 'workflow', label: 'Workflow Preview', icon: 'M4 6h16M4 10h16M4 14h16M4 18h16' },
  { id: 'recommendations', label: 'Recommendations', icon: 'M13 10V3L4 14h7v7l9-11h-7z' },
];

const priorityColor: Record<string, string> = {
  critical: 'critical',
  high: 'high',
  medium: 'medium',
  low: 'low',
  info: 'info',
};

const AIReconPage: React.FC = () => {
  const { user } = useAuthStore();
  const orgId = user?.organization_id ?? 'demo-org';

  const [activeTab, setActiveTab] = useState<TabId>('plan');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const [programName, setProgramName] = useState('Bug Bounty Program');
  const [scopeDomains, setScopeDomains] = useState('example.com, api.example.com');
  const [riskLevel, setRiskLevel] = useState('high');
  const [technologies, setTechnologies] = useState('nginx, react, fastapi');

  const [reconPlan, setReconPlan] = useState<any>(null);
  const [workflow, setWorkflow] = useState<any>(null);
  const [recommendations, setRecommendations] = useState<any>(null);

  const domainList = scopeDomains.split(',').map(d => d.trim()).filter(Boolean);
  const techList = technologies.split(',').map(t => t.trim()).filter(Boolean);

  const handleGeneratePlan = async () => {
    setLoading(true); setError('');
    try {
      const data = await generateReconPlan({
        organization_id: orgId,
        program_name: programName,
        scope_domains: domainList,
      });
      setReconPlan(data);
      setActiveTab('plan');
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? 'Plan generation failed. Ensure backend is running.');
    } finally { setLoading(false); }
  };

  const handleWorkflowPreview = async () => {
    setLoading(true); setError('');
    try {
      const data = await previewWorkflow({
        organization_id: orgId,
        program_name: programName,
        scope_domains: domainList,
        risk_level: riskLevel,
        technologies: techList,
      });
      setWorkflow(data);
      setActiveTab('workflow');
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? 'Workflow preview failed.');
    } finally { setLoading(false); }
  };

  const handleRecommendations = async () => {
    setLoading(true); setError('');
    try {
      const data = await getRecommendations(orgId);
      setRecommendations(data);
      setActiveTab('recommendations');
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? 'Recommendations failed.');
    } finally { setLoading(false); }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-start flex-wrap gap-4">
        <div>
          <div className="flex items-center space-x-3 mb-1">
            <h1 className="text-2xl font-bold text-white">AI Recon Planning</h1>
            <Badge variant="secondary">Phase 18</Badge>
          </div>
          <p className="text-gray-400 text-sm">
            AI-assisted attack surface intelligence — advisory only. All actions require human approval.
          </p>
        </div>
        <div className="flex items-center space-x-2 text-xs text-gray-500 bg-white/5 border border-white/10 rounded-lg px-3 py-2">
          <svg className="w-3.5 h-3.5 text-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
          </svg>
          <span>Advisory Only · Human Approval Required</span>
        </div>
      </div>

      {error && (
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}
          className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-sm text-red-400 flex items-center space-x-2">
          <svg className="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span>{error}</span>
        </motion.div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
        {/* Config Panel */}
        <Card className="xl:col-span-1">
          <h2 className="text-sm font-semibold text-gray-300 mb-4 flex items-center">
            <svg className="w-4 h-4 mr-2 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
            </svg>
            Configuration
          </h2>
          <div className="space-y-4">
            <div>
              <label className="text-xs text-gray-400 mb-1 block">Program Name</label>
              <input value={programName} onChange={e => setProgramName(e.target.value)}
                className="w-full bg-background-card/50 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-transparent transition-all"
                placeholder="My Bug Bounty" />
            </div>
            <div>
              <label className="text-xs text-gray-400 mb-1 block">Scope Domains</label>
              <textarea value={scopeDomains} onChange={e => setScopeDomains(e.target.value)} rows={3}
                className="w-full bg-background-card/50 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-transparent transition-all resize-none font-mono"
                placeholder="example.com, api.example.com" />
            </div>
            <div>
              <label className="text-xs text-gray-400 mb-1 block">Risk Level</label>
              <select value={riskLevel} onChange={e => setRiskLevel(e.target.value)}
                className="w-full bg-background-card/50 border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all">
                {['critical','high','medium','low'].map(r => <option key={r} value={r}>{r.charAt(0).toUpperCase()+r.slice(1)}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-400 mb-1 block">Technologies</label>
              <input value={technologies} onChange={e => setTechnologies(e.target.value)}
                className="w-full bg-background-card/50 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-transparent transition-all"
                placeholder="nginx, react, postgres" />
            </div>

            <div className="pt-2 space-y-2">
              <Button variant="primary" className="w-full text-sm py-2.5" onClick={handleGeneratePlan} disabled={loading}>
                {loading ? 'Generating...' : '⚡ Generate AI Plan'}
              </Button>
              <Button variant="secondary" className="w-full text-sm py-2.5" onClick={handleWorkflowPreview} disabled={loading}>
                🔄 Preview Workflow
              </Button>
              <Button variant="outline" className="w-full text-sm py-2.5" onClick={handleRecommendations} disabled={loading}>
                💡 Get Recommendations
              </Button>
            </div>
          </div>
        </Card>

        {/* Output Panel */}
        <div className="xl:col-span-3 space-y-4">
          {/* Tabs */}
          <div className="flex space-x-1 bg-white/5 border border-white/10 rounded-xl p-1">
            {TABS.map(tab => (
              <button key={tab.id} onClick={() => setActiveTab(tab.id)}
                className={`flex-1 flex items-center justify-center space-x-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
                  activeTab === tab.id ? 'bg-gradient-to-r from-primary/20 to-secondary/20 text-white border border-primary/30' : 'text-gray-400 hover:text-white hover:bg-white/5'
                }`}>
                <svg className="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d={tab.icon} />
                </svg>
                <span className="hidden sm:inline">{tab.label}</span>
              </button>
            ))}
          </div>

          <AnimatePresence mode="wait">
            {/* Plan Tab */}
            {activeTab === 'plan' && (
              <motion.div key="plan" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}>
                {!reconPlan ? (
                  <Card>
                    <div className="flex flex-col items-center justify-center py-16 text-center">
                      <div className="w-16 h-16 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center mb-4">
                        <svg className="w-8 h-8 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                        </svg>
                      </div>
                      <h3 className="text-white font-semibold mb-2">No Plan Generated Yet</h3>
                      <p className="text-gray-400 text-sm max-w-sm">Configure scope and click "Generate AI Plan" to get AI-assisted recon strategy recommendations.</p>
                    </div>
                  </Card>
                ) : (
                  <div className="space-y-4">
                    <Card>
                      <div className="flex items-start justify-between mb-4">
                        <div>
                          <h3 className="text-white font-bold text-lg">{reconPlan.recon_plan?.plan_name ?? 'AI Recon Plan'}</h3>
                          <p className="text-gray-400 text-sm mt-1">{reconPlan.recon_plan?.objective}</p>
                        </div>
                        <Badge variant="secondary">Pending Review</Badge>
                      </div>
                      <div className="grid grid-cols-3 gap-4 text-center mb-4">
                        <div className="p-3 bg-white/5 rounded-lg">
                          <div className="text-2xl font-bold text-white">{reconPlan.context_summary?.asset_count ?? 0}</div>
                          <div className="text-xs text-gray-400 mt-1">Assets</div>
                        </div>
                        <div className="p-3 bg-white/5 rounded-lg">
                          <div className="text-2xl font-bold text-white">{reconPlan.context_summary?.active_exposures ?? 0}</div>
                          <div className="text-xs text-gray-400 mt-1">Exposures</div>
                        </div>
                        <div className="p-3 bg-white/5 rounded-lg">
                          <div className="text-2xl font-bold text-primary">{Math.round((reconPlan.recon_plan?.confidence ?? 0.5) * 100)}%</div>
                          <div className="text-xs text-gray-400 mt-1">AI Confidence</div>
                        </div>
                      </div>
                      <div className="p-3 bg-secondary/10 border border-secondary/20 rounded-lg text-xs text-gray-300 flex items-start space-x-2">
                        <svg className="w-3.5 h-3.5 text-secondary mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                        </svg>
                        <span>{reconPlan.advisory_note}</span>
                      </div>
                    </Card>

                    {/* Phases */}
                    {(reconPlan.recon_plan?.phases ?? []).map((phase: any, i: number) => (
                      <Card key={i}>
                        <div className="flex items-center justify-between mb-3">
                          <div className="flex items-center space-x-3">
                            <div className="w-8 h-8 rounded-lg bg-primary/20 border border-primary/30 flex items-center justify-center text-primary font-bold text-sm">
                              {phase.priority}
                            </div>
                            <h4 className="text-white font-semibold">{phase.phase_name}</h4>
                          </div>
                          <span className="text-xs text-gray-400 font-mono">{phase.estimated_duration_minutes}m</span>
                        </div>
                        <p className="text-gray-400 text-sm mb-3">{phase.rationale}</p>
                        <div className="flex flex-wrap gap-2">
                          {(phase.scan_types ?? []).map((t: string) => (
                            <span key={t} className="text-xs bg-white/5 border border-white/10 text-gray-300 px-2 py-1 rounded-md font-mono">{t}</span>
                          ))}
                        </div>
                      </Card>
                    ))}
                  </div>
                )}
              </motion.div>
            )}

            {/* Workflow Tab */}
            {activeTab === 'workflow' && (
              <motion.div key="workflow" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}>
                {!workflow ? (
                  <Card>
                    <div className="flex flex-col items-center justify-center py-16 text-center">
                      <div className="w-16 h-16 rounded-2xl bg-secondary/10 border border-secondary/20 flex items-center justify-center mb-4">
                        <svg className="w-8 h-8 text-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M4 6h16M4 10h16M4 14h16M4 18h16" />
                        </svg>
                      </div>
                      <h3 className="text-white font-semibold mb-2">No Workflow Generated</h3>
                      <p className="text-gray-400 text-sm max-w-sm">Click "Preview Workflow" to generate an AI pipeline recommendation.</p>
                    </div>
                  </Card>
                ) : (
                  <Card>
                    <div className="flex items-start justify-between mb-6">
                      <div>
                        <h3 className="text-white font-bold text-lg">{workflow.workflow?.workflow_name}</h3>
                        <p className="text-gray-400 text-sm mt-1">{workflow.workflow?.description}</p>
                      </div>
                      <Badge variant="medium">Preview</Badge>
                    </div>
                    <div className="relative">
                      <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-white/10"></div>
                      <div className="space-y-4">
                        {(workflow.workflow?.stages ?? []).map((stage: any, i: number) => (
                          <motion.div key={stage.stage_id} initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.1 }}
                            className="relative flex items-start ml-10">
                            <div className="absolute -left-[38px] w-8 h-8 rounded-full bg-background border-2 border-primary/50 flex items-center justify-center text-xs font-bold text-primary">
                              {i + 1}
                            </div>
                            <div className="flex-1 p-4 bg-white/5 border border-white/10 rounded-xl hover:border-primary/30 transition-colors">
                              <div className="flex items-center justify-between mb-2">
                                <span className="font-semibold text-white text-sm">{stage.stage_name}</span>
                                <div className="flex items-center space-x-2">
                                  <span className="text-xs font-mono text-gray-400">{stage.estimated_minutes ?? '?'}m</span>
                                  <span className="text-xs bg-yellow-500/10 text-yellow-400 border border-yellow-500/20 rounded px-1.5 py-0.5">Needs Approval</span>
                                </div>
                              </div>
                              <span className="text-xs text-primary font-mono bg-primary/10 px-2 py-0.5 rounded">{stage.tool_category}</span>
                              {stage.dependencies?.length > 0 && (
                                <div className="mt-2 text-xs text-gray-500">Depends on: {stage.dependencies.join(', ')}</div>
                              )}
                            </div>
                          </motion.div>
                        ))}
                      </div>
                    </div>
                    <div className="mt-4 p-3 bg-yellow-500/10 border border-yellow-500/20 rounded-lg text-xs text-yellow-400 flex items-center space-x-2">
                      <svg className="w-3.5 h-3.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                      </svg>
                      <span>{workflow.security_note}</span>
                    </div>
                  </Card>
                )}
              </motion.div>
            )}

            {/* Recommendations Tab */}
            {activeTab === 'recommendations' && (
              <motion.div key="recs" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}>
                {!recommendations ? (
                  <Card>
                    <div className="flex flex-col items-center justify-center py-16 text-center">
                      <div className="w-16 h-16 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center mb-4">
                        <svg className="w-8 h-8 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M13 10V3L4 14h7v7l9-11h-7z" />
                        </svg>
                      </div>
                      <h3 className="text-white font-semibold mb-2">No Recommendations Yet</h3>
                      <p className="text-gray-400 text-sm max-w-sm">Click "Get Recommendations" to get AI-powered next-action suggestions.</p>
                    </div>
                  </Card>
                ) : (
                  <div className="space-y-4">
                    {/* Next Actions */}
                    {(recommendations.recommendations?.next_actions?.recommendations ?? []).map((rec: any, i: number) => (
                      <Card key={i} glowHover>
                        <div className="flex items-start justify-between">
                          <div className="flex items-start space-x-3 flex-1">
                            <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-sm font-bold shrink-0 ${
                              rec.priority === 1 ? 'bg-red-500/20 text-red-400 border border-red-500/30' :
                              rec.priority === 2 ? 'bg-orange-500/20 text-orange-400 border border-orange-500/30' :
                              'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                            }`}>P{rec.priority}</div>
                            <div className="flex-1">
                              <h4 className="text-white font-semibold text-sm">{rec.title}</h4>
                              <p className="text-gray-400 text-xs mt-1">{rec.rationale}</p>
                              <div className="flex items-center space-x-2 mt-2">
                                <span className="text-xs text-gray-500 bg-white/5 px-2 py-0.5 rounded">{rec.action_type}</span>
                                <span className="text-xs text-gray-500">{rec.effort_estimate} effort</span>
                                <span className="text-xs text-green-400">{rec.expected_impact}</span>
                              </div>
                            </div>
                          </div>
                        </div>
                      </Card>
                    ))}

                    {/* Follow-up Scans */}
                    {(recommendations.recommendations?.followup_scans?.followup_scans ?? []).length > 0 && (
                      <Card>
                        <h3 className="text-white font-semibold mb-4 flex items-center">
                          <svg className="w-4 h-4 mr-2 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                          </svg>
                          Follow-up Scans
                        </h3>
                        <div className="space-y-3">
                          {(recommendations.recommendations.followup_scans.followup_scans ?? []).map((scan: any, i: number) => (
                            <div key={i} className="p-3 bg-white/5 border border-white/10 rounded-lg">
                              <div className="flex items-center justify-between mb-1">
                                <span className="text-sm text-white font-mono">{scan.scan_type}</span>
                                <Badge variant={(['critical','high','medium','low','info'] as const)[Math.min(scan.priority - 1, 4)]}>P{scan.priority}</Badge>
                              </div>
                              <p className="text-xs text-gray-400">{scan.rationale}</p>
                              <p className="text-xs text-yellow-400 mt-1">⚠ {scan.scope_constraint}</p>
                            </div>
                          ))}
                        </div>
                      </Card>
                    )}

                    <div className="p-3 bg-secondary/10 border border-secondary/20 rounded-lg text-xs text-gray-400 flex items-center space-x-2">
                      <svg className="w-3.5 h-3.5 text-secondary shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <span>All recommendations are advisory-only. Human review and approval required before execution.</span>
                    </div>
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
};

export default AIReconPage;
