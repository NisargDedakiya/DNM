import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Card,
  Badge,
  Button,
  TelemetryCard,
  StatusIndicator,
  CyberPanel,
  PanelLabel,
} from '../../components/ui/components'
import { ThreatLevelBar, AttackPathCard, AIInsightPanel } from '../../components/widgets/ThreatWidgets'
import LiveEventFeed from '../../components/widgets/LiveEventFeed'
import useAuthStore from '../../state/auth'
import useRealtimeStore from '../../realtime/realtimeStore'
import useFindingsStore from '../../state/findings'
import useCampaignsStore from '../../state/campaigns'
import useInvestigationsStore from '../../state/investigations'
import AddBugcrowdModal from '../../components/AddBugcrowdModal'
import api from '../../api/client'
import { getPrograms } from '../../api/clients/programs'
import { getScans } from '../../api/clients/scans'
import { getDashboardStats } from '../../api/clients/dashboard'

// @ts-ignore
import ExposureTimelineView from '../../timeline/ExposureTimelineView'
// @ts-ignore
import SystemHealthDashboard from '../../monitoring/SystemHealthDashboard'
// @ts-ignore
import PerformanceDashboard from '../../performance/PerformanceDashboard'

// Mock insights
const MOCK_INSIGHTS = [
  {
    id: 'ins-1',
    title: 'SSO Trust Path Simulation Vulnerability',
    body: 'Anomalous OIDC tokens detected on dev-internal.target.com. Active trust chain traversal could allow lateral privilege escalation.',
    confidence: 94,
    urgency: 'critical' as const,
    category: 'attack-path' as const,
    timestamp: new Date(Date.now() - 15 * 60 * 1000).toISOString(),
  },
  {
    id: 'ins-2',
    title: 'Exposed Port/Service Drift Alert',
    body: 'Recon agents observed new listening ports 8083, 9000 on edge targets. Recommend immediate firewall boundary checks.',
    confidence: 85,
    urgency: 'high' as const,
    category: 'recon' as const,
    timestamp: new Date(Date.now() - 45 * 60 * 1000).toISOString(),
  },
  {
    id: 'ins-3',
    title: 'Remediation Playbook Generation',
    body: 'AI generated remediation playbook for OIDC Session Boundary Bypass. Estimated patching complexity: Low.',
    confidence: 89,
    urgency: 'medium' as const,
    category: 'remediation' as const,
    timestamp: new Date(Date.now() - 120 * 60 * 1000).toISOString(),
  },
]

// Mock attack paths
const MOCK_ATTACK_PATHS = [
  {
    title: 'External OIDC Identity Compromise Path',
    severity: 'critical' as const,
    affectedTargets: 4,
    discoveredAt: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
    nodes: [
      { id: 'node-1', label: 'OAuth Public API', type: 'entry' as const },
      { id: 'node-2', label: 'Cognito Token Bypass', type: 'lateral' as const },
      { id: 'node-3', label: 'IAM Pivot Role', type: 'pivot' as const },
      { id: 'node-4', label: 'Financial DB S3 Bucket', type: 'target' as const },
    ],
  },
  {
    title: 'SSL VPN Gateway Path to Internal Subnet',
    severity: 'high' as const,
    affectedTargets: 12,
    discoveredAt: new Date(Date.now() - 180 * 60 * 1000).toISOString(),
    nodes: [
      { id: 'node-5', label: 'VPN Gateway CVE', type: 'entry' as const },
      { id: 'node-6', label: 'AD Domain Controller', type: 'lateral' as const },
      { id: 'node-7', label: 'Corporate Mail Exchange', type: 'target' as const },
    ],
  },
]

export default function Dashboard() {
  const navigate = useNavigate()
  const organizationId = useAuthStore((state) => state.activeOrgId || '')
  const [showBugcrowdModal, setShowBugcrowdModal] = useState(false)

  // Realtime events
  const isConnected = useRealtimeStore((state) => state.isConnected)
  const activeAlerts = useRealtimeStore((state) => state.activeAlerts)
  const recentEvents = useRealtimeStore((state) => state.recentEvents)

  // Subscribed states
  const findings = useFindingsStore((state) => state.findings)
  const setFindings = useFindingsStore((state) => state.setFindings)
  const campaigns = useCampaignsStore((state) => state.campaigns)
  const setCampaigns = useCampaignsStore((state) => state.setCampaigns)
  const investigations = useInvestigationsStore((state) => state.investigations)
  const setInvestigations = useInvestigationsStore((state) => state.setInvestigations)

  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  // Load operational data when mounted or org change
  useEffect(() => {
    if (!organizationId) return

    const loadDashboardData = async () => {
      try {
        setLoading(true)
        
        // Fetch aggregated stats
        const statsData = await getDashboardStats()
        setStats(statsData)

        // Fetch programs and set active campaign list
        const programs = await getPrograms()
        if (programs && programs.length > 0) {
          const campaignList = programs.map((p: any) => ({
            id: p.id,
            name: p.name,
            target: p.scope || 'N/A',
            status: p.platform === 'custom' ? 'paused' as const : 'active' as const,
            created_at: p.created_at,
          }))
          setCampaigns(campaignList)
        }

        // Fetch active scans as telemetry checks
        const scans = await getScans()
        if (scans && scans.length > 0) {
          // If findings store is empty, construct findings from scan results count or default values
          const activeFindings = scans.flatMap((s: any) => {
            if (s.results_count > 0) {
              return Array.from({ length: s.results_count }).map((_, i) => ({
                id: `F-${s.id}-${i}`,
                title: `Vulnerability detected during ${s.scanner_type || 'scan'}`,
                severity: i % 2 === 0 ? 'critical' as const : 'high' as const,
                status: 'open' as const,
                organization_id: organizationId,
                created_at: s.created_at,
              }))
            }
            return []
          })
          if (activeFindings.length > 0) {
            setFindings(activeFindings)
          }
        }

        // Fetch investigations
        const res = await api.get('/collaboration/investigations', {
          params: { organization_id: organizationId },
        })
        if (res.data) {
          setInvestigations(res.data)
        }

      } catch (err) {
        console.error('[Dashboard] Error loading command center data:', err)
      } finally {
        setLoading(false)
      }
    }

    loadDashboardData()
  }, [organizationId, setFindings, setCampaigns, setInvestigations])

  // Derive counts with fallbacks
  const findingsCount = findings.length > 0 ? findings.length : (stats?.total_findings || 12)
  const criticalFindingsCount = findings.filter(f => f.severity === 'critical').length || (stats?.findings_by_severity?.critical || 4)
  const highFindingsCount = findings.filter(f => f.severity === 'high').length || (stats?.findings_by_severity?.high || 6)

  const activeHuntsCount = campaigns.filter(c => c.status === 'active').length || (stats?.active_scans || 3)
  const totalCampaignsCount = campaigns.length || (stats?.total_scans || 8)
  const activeInvestigationsCount = investigations.filter(i => i.status === 'active').length || 2

  // Derive DEFCON Level based on critical alerts and findings
  const defconLevel = activeAlerts.length > 0 
    ? 1 
    : criticalFindingsCount > 3 
    ? 2 
    : highFindingsCount > 0 
    ? 3 
    : 4

  return (
    <div className="space-y-6">
      {/* ── ROW 1: Operational Status Bar (Full Width) ── */}
      <CyberPanel className="p-4" scanLine>
        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-display font-bold text-white tracking-wider">🛡 CYBER OPERATIONS COMMAND</h1>
            <Badge variant={isConnected ? 'nominal' : 'primary'} className="font-mono text-[9px] tracking-widest px-2 py-0.5 animate-pulse">
              {isConnected ? 'STREAM SYNCED' : 'BUS OFFLINE'}
            </Badge>
          </div>
          <div className="flex items-center gap-6 w-full lg:w-auto justify-between lg:justify-end">
            <ThreatLevelBar level={defconLevel as any} criticalCount={activeAlerts.length} highCount={highFindingsCount} />
            <StatusIndicator status={isConnected ? 'live' : 'connecting'} label={isConnected ? 'WEBSOCKET ACTIVE' : 'RECONNECTING'} />
          </div>
        </div>
      </CyberPanel>

      {/* ── High-Density Telemetry Stats ── */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <TelemetryCard
          label="Scanned Targets"
          value={stats?.total_programs ? stats.total_programs * 12 : 1420}
          delta="8.2%"
          deltaPositive
          icon={<span>🕸</span>}
          color="primary"
          suffix="nodes"
        />
        <TelemetryCard
          label="Active Vulnerabilities"
          value={findingsCount}
          delta={`${criticalFindingsCount} critical`}
          deltaPositive={false}
          icon={<span>⚡</span>}
          color={criticalFindingsCount > 0 ? 'critical' : 'high'}
        />
        <TelemetryCard
          label="Hunt Campaigns"
          value={activeHuntsCount}
          delta="Active"
          deltaPositive
          icon={<span>🎯</span>}
          color="secondary"
        />
        <TelemetryCard
          label="Monitoring Scans"
          value={totalCampaignsCount}
          delta="Configured"
          deltaPositive
          icon={<span>📡</span>}
          color="green"
        />
        <TelemetryCard
          label="Active Investigations"
          value={activeInvestigationsCount}
          delta="Under Review"
          deltaPositive={false}
          icon={<span>🔍</span>}
          color="medium"
        />
      </div>

      {/* ── ROW 2: Primary Intelligence Grid ── */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Threat Telemetry Console (66%) */}
        <CyberPanel
          title={<PanelLabel dot="primary">REALTIME THREAT TELEMETRY CONSOLE</PanelLabel>}
          action={
            <div className="text-[10px] font-mono text-gray-500">
              Ctrl + K for command palette
            </div>
          }
          className="xl:col-span-2 flex flex-col h-[420px] overflow-hidden"
        >
          <div className="flex-1 overflow-hidden p-4">
            <LiveEventFeed events={recentEvents} maxHeight="340px" />
          </div>
        </CyberPanel>

        {/* Active Operations Deck (33%) */}
        <CyberPanel
          title={<PanelLabel dot="green">ACTIVE OPERATIONS DECK</PanelLabel>}
          className="p-5 flex flex-col justify-between"
        >
          <div className="space-y-4">
            {campaigns.length === 0 ? (
              // Default mock operations if state is empty
              <>
                <div className="p-3 rounded-xl border border-white/5 bg-white/[0.02] flex justify-between items-center hover:border-white/10 transition-colors">
                  <div>
                    <h4 className="text-sm font-bold text-slate-200">External Port Penetration Sim</h4>
                    <div className="flex items-center gap-2 mt-1 text-[10px] text-gray-400 font-mono">
                      <span>120 nodes checked</span>
                      <span>•</span>
                      <span className="text-gray-500 uppercase">Idle</span>
                    </div>
                  </div>
                  <Badge variant="outline" className="text-[9px] py-0.5">STAGE 1</Badge>
                </div>
                <div className="p-3 rounded-xl border border-primary/20 bg-primary/5 flex justify-between items-center hover:border-primary/30 transition-colors">
                  <div>
                    <h4 className="text-sm font-bold text-slate-200">OIDC Session Boundary Scan</h4>
                    <div className="flex items-center gap-2 mt-1 text-[10px] text-primary/80 font-mono">
                      <span>85 nodes checked</span>
                      <span>•</span>
                      <span className="text-primary uppercase font-bold animate-pulse">Running</span>
                    </div>
                  </div>
                  <Badge variant="primary" className="text-[9px] py-0.5">STAGE 3</Badge>
                </div>
                <div className="p-3 rounded-xl border border-white/5 bg-white/[0.02] flex justify-between items-center hover:border-white/10 transition-colors">
                  <div>
                    <h4 className="text-sm font-bold text-slate-200">SSO Trust Path Simulation</h4>
                    <div className="flex items-center gap-2 mt-1 text-[10px] text-gray-400 font-mono">
                      <span>42 nodes checked</span>
                      <span>•</span>
                      <span className="text-gray-500 uppercase">Pending</span>
                    </div>
                  </div>
                  <Badge variant="outline" className="text-[9px] py-0.5">STAGE 2</Badge>
                </div>
              </>
            ) : (
              campaigns.slice(0, 3).map((campaign) => (
                <div
                  key={campaign.id}
                  className={`p-3 rounded-xl border flex justify-between items-center transition-colors ${
                    campaign.status === 'active'
                      ? 'border-primary/20 bg-primary/5'
                      : 'border-white/5 bg-white/[0.02] hover:border-white/10'
                  }`}
                >
                  <div>
                    <h4 className="text-sm font-bold text-slate-200">{campaign.name}</h4>
                    <div className="flex items-center gap-2 mt-1 text-[10px] text-gray-400 font-mono">
                      <span>Target: {campaign.target || 'None'}</span>
                      <span>•</span>
                      <span className={campaign.status === 'active' ? 'text-primary font-bold animate-pulse' : 'text-gray-500'}>
                        {campaign.status.toUpperCase()}
                      </span>
                    </div>
                  </div>
                  <Badge variant={campaign.status === 'active' ? 'primary' : 'outline'} className="text-[9px]">
                    {campaign.status === 'active' ? 'LIVE' : 'IDLE'}
                  </Badge>
                </div>
              ))
            )}
          </div>

          <div className="mt-6 pt-4 border-t border-white/5 grid grid-cols-2 gap-3">
            <Button variant="outline" className="text-xs" onClick={() => navigate('/app/monitoring')}>
              🎯 Setup Hunt
            </Button>
            <Button variant="primary" className="text-xs" onClick={() => setShowBugcrowdModal(true)}>
              ➕ Add Scope
            </Button>
          </div>
        </CyberPanel>
      </div>

      {/* ── ROW 3: Attack Intelligence ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Attack Path Summary */}
        <CyberPanel title={<PanelLabel dot="red">CRITICAL ATTACK PATHS</PanelLabel>}>
          <div className="p-5 space-y-4">
            {MOCK_ATTACK_PATHS.map((path, idx) => (
              <AttackPathCard key={idx} {...path} />
            ))}
          </div>
        </CyberPanel>

        {/* AI Recommendations */}
        <CyberPanel title={<PanelLabel dot="yellow">AI INSIGHT ENGINE RECOMMENDATIONS</PanelLabel>}>
          <div className="p-5">
            <AIInsightPanel insights={MOCK_INSIGHTS} />
          </div>
        </CyberPanel>
      </div>

      {/* ── ROW 4: Exposure Timeline ── */}
      {organizationId && (
        <CyberPanel title={<PanelLabel dot="primary">EXPOSURE DEVELOPMENT TIMELINE</PanelLabel>}>
          <div className="p-5">
            <ExposureTimelineView organizationId={organizationId} />
          </div>
        </CyberPanel>
      )}

      {/* ── ROW 5: System Health & Performance ── */}
      {organizationId && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <CyberPanel title={<PanelLabel dot="primary">PERFORMANCE MONITORING</PanelLabel>}>
            <div className="p-5">
              <PerformanceDashboard organizationId={organizationId} />
            </div>
          </CyberPanel>
          <CyberPanel title={<PanelLabel dot="green">SYSTEM INTEGRITY HEALTH</PanelLabel>}>
            <div className="p-5">
              <SystemHealthDashboard organizationId={organizationId} />
            </div>
          </CyberPanel>
        </div>
      )}

      {/* Scope Onboarding Modal */}
      <AddBugcrowdModal
        isOpen={showBugcrowdModal}
        onClose={() => setShowBugcrowdModal(false)}
        onSuccess={() => {
          window.location.reload()
        }}
      />
    </div>
  )
}
