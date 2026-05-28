import React, { useEffect, useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import useAuthStore from '../../state/auth'
import { Button } from '../../components/ui/components'
import { IngestionPipelinePanel } from '../../components/integrations/IngestionPipelinePanel'
import {
  ingestBugcrowdEngagement,
  listBugcrowdPrograms,
  BugcrowdProgram,
} from '../../api/clients/bugcrowd'
import {
  connectHackerOne,
  syncHackerOnePrograms,
  listHackerOnePrograms,
  HackerOneProgram,
} from '../../api/clients/integrations'
import { createProgram, getPrograms, Program } from '../../api/clients/programs'

// ─── Types ───────────────────────────────────────────────────────────────────

type ActiveTab = 'programs' | 'ingest' | 'credentials'
type DetectedPlatform = 'bugcrowd' | 'hackerone' | 'custom' | null

// ─── Platform badge ──────────────────────────────────────────────────────────

const PlatformBadge: React.FC<{ platform: 'bugcrowd' | 'hackerone' | 'custom' | string }> = ({
  platform,
}) => {
  const cfg = {
    bugcrowd: { bg: 'bg-amber-400/10', text: 'text-amber-400', border: 'border-amber-400/20', label: 'Bugcrowd' },
    hackerone: { bg: 'bg-sky-400/10', text: 'text-sky-400', border: 'border-sky-400/20', label: 'HackerOne' },
    custom: { bg: 'bg-purple-400/10', text: 'text-purple-400', border: 'border-purple-400/20', label: 'Custom' },
  }[platform] ?? { bg: 'bg-gray-400/10', text: 'text-gray-400', border: 'border-gray-400/20', label: platform }

  return (
    <span
      className={`text-[10px] ${cfg.bg} ${cfg.text} border ${cfg.border} px-2 py-0.5 rounded font-mono uppercase font-bold`}
    >
      {cfg.label}
    </span>
  )
}

// ─── Program card ────────────────────────────────────────────────────────────

const ProgramCard: React.FC<{
  platform: 'bugcrowd' | 'hackerone' | 'custom'
  title: string
  subtitle: string
  meta?: React.ReactNode
  statusBadge?: React.ReactNode
}> = ({ platform, title, subtitle, meta, statusBadge }) => (
  <motion.div
    initial={{ opacity: 0, y: 10 }}
    animate={{ opacity: 1, y: 0 }}
    className="relative group bg-background-card/45 border border-white/5 rounded-2xl p-5 hover:border-primary/45 transition-all duration-300 flex flex-col justify-between"
  >
    <div>
      <div className="flex items-center justify-between mb-3">
        <PlatformBadge platform={platform} />
        {statusBadge}
      </div>
      <h3 className="text-base font-bold text-white truncate">{title}</h3>
      <p className="text-xs text-gray-400 mt-1.5 truncate">{subtitle}</p>
    </div>
    {meta && (
      <div className="mt-5 pt-4 border-t border-white/5">{meta}</div>
    )}
  </motion.div>
)

// ─── Notification banner ─────────────────────────────────────────────────────

const Banner: React.FC<{ type: 'success' | 'error'; message: string; onClose: () => void }> = ({
  type,
  message,
  onClose,
}) => (
  <motion.div
    initial={{ opacity: 0, y: -8 }}
    animate={{ opacity: 1, y: 0 }}
    exit={{ opacity: 0, y: -8 }}
    className={`flex items-start gap-3 p-4 rounded-xl border text-sm ${
      type === 'success'
        ? 'bg-green-500/10 border-green-500/30 text-green-400'
        : 'bg-red-500/10 border-red-500/30 text-red-400'
    }`}
  >
    <span className="text-base mt-0.5">{type === 'success' ? '✓' : '⚠'}</span>
    <p className="flex-1">{message}</p>
    <button onClick={onClose} className="opacity-50 hover:opacity-100 transition-opacity text-base leading-none">×</button>
  </motion.div>
)

// ─── Main Component ──────────────────────────────────────────────────────────

export const ProgramsPage: React.FC = () => {
  const { activeOrgId } = useAuthStore()
  const orgId = activeOrgId || ''
  const [activeTab, setActiveTab] = useState<ActiveTab>('programs')

  // Program lists
  const [customPrograms, setCustomPrograms] = useState<Program[]>([])
  const [bugcrowdPrograms, setBugcrowdPrograms] = useState<BugcrowdProgram[]>([])
  const [h1Programs, setH1Programs] = useState<HackerOneProgram[]>([])
  const [loading, setLoading] = useState(false)

  // Alerts
  const [success, setSuccess] = useState('')
  const [error, setError] = useState('')

  // Ingest form
  const [url, setUrl] = useState('')
  const [detectedPlatform, setDetectedPlatform] = useState<DetectedPlatform>(null)
  const [customName, setCustomName] = useState('')
  const [customScope, setCustomScope] = useState('')
  const [ingesting, setIngesting] = useState(false)

  // Pipeline panel
  const [pipelineVisible, setPipelineVisible] = useState(false)
  const [pipelinePlatform, setPipelinePlatform] = useState<'bugcrowd' | 'hackerone' | null>(null)

  // Credentials
  const [h1User, setH1User] = useState('')
  const [h1Token, setH1Token] = useState('')
  const [credLoading, setCredLoading] = useState(false)

  // ─── Load Programs ─────────────────────────────────────────────────────

  const loadAllPrograms = useCallback(async () => {
    if (!orgId) return
    setLoading(true)
    try {
      const [customData, bcData, h1Data] = await Promise.allSettled([
        getPrograms(),
        listBugcrowdPrograms(orgId),
        listHackerOnePrograms(orgId),
      ])
      if (customData.status === 'fulfilled') setCustomPrograms(customData.value)
      if (bcData.status === 'fulfilled') setBugcrowdPrograms(bcData.value)
      if (h1Data.status === 'fulfilled') setH1Programs(h1Data.value?.programs || [])
    } finally {
      setLoading(false)
    }
  }, [orgId])

  useEffect(() => {
    loadAllPrograms()
  }, [loadAllPrograms])

  // ─── Platform Detection ────────────────────────────────────────────────

  useEffect(() => {
    const u = url.trim().toLowerCase()
    if (u.includes('bugcrowd.com')) setDetectedPlatform('bugcrowd')
    else if (u.includes('hackerone.com')) setDetectedPlatform('hackerone')
    else if (u !== '') setDetectedPlatform('custom')
    else setDetectedPlatform(null)
  }, [url])

  // ─── Ingest handler ────────────────────────────────────────────────────

  const handleIngest = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!url || !orgId) return
    setIngesting(true)
    setError('')
    setSuccess('')

    try {
      if (detectedPlatform === 'bugcrowd') {
        // Show pipeline panel BEFORE calling ingest — events will stream in
        setPipelinePlatform('bugcrowd')
        setPipelineVisible(true)

        const res = await ingestBugcrowdEngagement(orgId, url)
        if (res.success) {
          setUrl('')
          loadAllPrograms()
        } else {
          setError(res.message || 'Ingestion failed.')
        }
      } else if (detectedPlatform === 'hackerone') {
        const handle = url.split('/').filter(Boolean).pop() || 'program'
        await createProgram({
          name: `HackerOne: ${handle}`,
          platform: 'hackerone',
          scope: url,
          description: 'HackerOne program URL-based ingestion.',
        })
        setSuccess(`HackerOne handle "${handle}" saved. Use Integrations Setup to sync all scopes via API.`)
        setUrl('')
        loadAllPrograms()
      } else if (detectedPlatform === 'custom') {
        await createProgram({
          name: customName || 'Custom Scope Segment',
          platform: 'custom',
          scope: customScope,
          description: 'Custom asset scope segment.',
        })
        setSuccess('Custom scope segment created.')
        setUrl('')
        setCustomName('')
        setCustomScope('')
        loadAllPrograms()
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Scope ingestion failed.')
    } finally {
      setIngesting(false)
    }
  }

  // ─── Credentials / HackerOne sync ─────────────────────────────────────

  const handleCredentials = async (e: React.FormEvent) => {
    e.preventDefault()
    setCredLoading(true)
    setError('')
    setSuccess('')

    // Show pipeline before sync
    setPipelinePlatform('hackerone')
    setPipelineVisible(true)

    try {
      await connectHackerOne(orgId, { username: h1User, api_token: h1Token })
      await syncHackerOnePrograms(orgId, { username: h1User, api_token: h1Token })
      setSuccess('HackerOne synchronized successfully.')
      loadAllPrograms()
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'HackerOne connection failed.')
    } finally {
      setCredLoading(false)
    }
  }

  // ─── Pipeline callbacks ────────────────────────────────────────────────

  const handlePipelineComplete = (data: any) => {
    if (!success) {
      const platform = pipelinePlatform === 'hackerone' ? 'HackerOne' : 'Bugcrowd'
      setSuccess(
        data.message ||
          `${platform} pipeline complete. ${data.assets_imported ?? data.total ?? ''} items processed.`
      )
    }
  }

  const handlePipelineError = (err: string) => {
    if (!error) setError(err)
  }

  // ─── Derived state ─────────────────────────────────────────────────────

  const totalPrograms =
    customPrograms.length + bugcrowdPrograms.length + h1Programs.length

  const tabLabels: Record<ActiveTab, string> = {
    programs: `Connected Programs ${totalPrograms > 0 ? `(${totalPrograms})` : ''}`,
    ingest: 'Ingest Scope Wizard',
    credentials: 'Integrations Setup',
  }

  // ─── Render ────────────────────────────────────────────────────────────

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-extrabold text-white tracking-tight glow-primary">
          Integrated Program Control
        </h1>
        <p className="text-sm text-gray-400 mt-2">
          Ingest Bugcrowd engagements and HackerOne programs into realtime attack surface intelligence workflows.
        </p>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: 'Total Programs', value: totalPrograms, color: 'text-white' },
          { label: 'Bugcrowd', value: bugcrowdPrograms.length, color: 'text-amber-400' },
          { label: 'HackerOne', value: h1Programs.length, color: 'text-sky-400' },
        ].map((s) => (
          <div key={s.label} className="bg-background-card/40 border border-white/5 rounded-xl p-4 text-center">
            <div className={`text-2xl font-bold ${s.color}`}>{s.value}</div>
            <div className="text-xs text-gray-500 mt-1">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Tab Navigation */}
      <div className="flex border-b border-white/10 space-x-8">
        {(Object.keys(tabLabels) as ActiveTab[]).map((tab) => (
          <button
            key={tab}
            id={`programs-tab-${tab}`}
            onClick={() => setActiveTab(tab)}
            className={`pb-4 text-sm font-semibold tracking-wider uppercase border-b-2 transition-all duration-300 ${
              activeTab === tab
                ? 'border-primary text-primary'
                : 'border-transparent text-gray-400 hover:text-white'
            }`}
          >
            {tabLabels[tab]}
          </button>
        ))}
      </div>

      {/* Notifications */}
      <AnimatePresence>
        {success && (
          <Banner type="success" message={success} onClose={() => setSuccess('')} />
        )}
        {error && (
          <Banner type="error" message={error} onClose={() => setError('')} />
        )}
      </AnimatePresence>

      {/* Tab Content */}
      <AnimatePresence mode="wait">
        {/* ── Programs Tab ── */}
        {activeTab === 'programs' && (
          <motion.div
            key="programs"
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -15 }}
            className="space-y-6"
          >
            {loading && (
              <div className="text-gray-500 text-sm py-8">
                <div className="flex items-center gap-3">
                  <div className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                  Querying active operational targets...
                </div>
              </div>
            )}

            {!loading && totalPrograms === 0 && (
              <div className="py-16 text-center text-gray-500 border border-white/5 rounded-2xl bg-white/[0.01]">
                <div className="text-4xl mb-4">🎯</div>
                <p className="text-sm">No operational program segments found.</p>
                <p className="text-xs mt-2 text-gray-600">
                  Click <span className="text-primary">&ldquo;Ingest Scope Wizard&rdquo;</span> to get started.
                </p>
              </div>
            )}

            {/* Bugcrowd cards */}
            {bugcrowdPrograms.length > 0 && (
              <div>
                <h3 className="text-xs font-bold text-amber-400 uppercase tracking-widest mb-3">
                  Bugcrowd Programs
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {bugcrowdPrograms.map((p) => (
                    <ProgramCard
                      key={p.id}
                      platform="bugcrowd"
                      title={p.name}
                      subtitle={p.engagement_url}
                      meta={
                        <div className="flex items-center justify-between text-xs text-gray-400">
                          <span>
                            <strong className="text-white">{p.assets_count}</strong> Target Scopes
                          </span>
                          <span className="text-gray-500 text-[10px]">
                            {p.last_synced_at
                              ? new Date(p.last_synced_at).toLocaleDateString()
                              : 'Never synced'}
                          </span>
                        </div>
                      }
                      statusBadge={
                        <span
                          className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded border ${
                            p.status === 'active'
                              ? 'bg-green-500/10 text-green-400 border-green-500/20'
                              : 'bg-gray-500/10 text-gray-400 border-gray-500/20'
                          }`}
                        >
                          {p.status}
                        </span>
                      }
                    />
                  ))}
                </div>
              </div>
            )}

            {/* HackerOne cards */}
            {h1Programs.length > 0 && (
              <div>
                <h3 className="text-xs font-bold text-sky-400 uppercase tracking-widest mb-3">
                  HackerOne Programs
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {h1Programs.map((p) => (
                    <ProgramCard
                      key={p.id}
                      platform="hackerone"
                      title={p.name}
                      subtitle={`@${p.handle}`}
                      meta={
                        <div className="flex items-center justify-between text-xs text-gray-400">
                          <span>
                            Bounty: <strong className="text-white">{p.bounty_enabled ? 'Yes' : 'No'}</strong>
                          </span>
                          <span className="text-gray-500 text-[10px]">
                            {p.synced_at ? new Date(p.synced_at).toLocaleDateString() : 'Never'}
                          </span>
                        </div>
                      }
                      statusBadge={
                        <span className="text-[10px] uppercase bg-green-500/10 text-green-400 border border-green-500/20 px-2 py-0.5 rounded font-bold">
                          Linked
                        </span>
                      }
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Custom programs */}
            {customPrograms.length > 0 && (
              <div>
                <h3 className="text-xs font-bold text-purple-400 uppercase tracking-widest mb-3">
                  Custom Scope Segments
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {customPrograms.map((p) => (
                    <ProgramCard
                      key={p.id}
                      platform="custom"
                      title={p.name}
                      subtitle={p.description || 'Custom network/domain asset scope.'}
                      meta={
                        <div className="text-xs text-gray-400">
                          Platform: <strong className="text-white">{p.platform || 'General'}</strong>
                        </div>
                      }
                      statusBadge={
                        <span className="text-[10px] uppercase bg-primary/10 text-primary border border-primary/20 px-2 py-0.5 rounded font-bold">
                          Loaded
                        </span>
                      }
                    />
                  ))}
                </div>
              </div>
            )}
          </motion.div>
        )}

        {/* ── Ingest Tab ── */}
        {activeTab === 'ingest' && (
          <motion.div
            key="ingest"
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -15 }}
            className="grid grid-cols-1 lg:grid-cols-2 gap-6"
          >
            {/* Form */}
            <div className="relative group">
              <div className="absolute -inset-[1px] bg-gradient-to-r from-primary to-secondary rounded-2xl opacity-60 blur-sm" />
              <div className="relative glass-panel p-8 shadow-2xl rounded-2xl border border-white/10 bg-background-card/85">
                <h3 className="text-xl font-bold text-white mb-2">Import Operational Scope</h3>
                <p className="text-xs text-gray-500 mb-6">
                  Paste a Bugcrowd engagement URL, HackerOne program URL, or define a custom scope.
                  The AI pipeline activates automatically.
                </p>

                <form onSubmit={handleIngest} className="space-y-5">
                  <div>
                    <label htmlFor="ingest-url" className="block text-sm font-semibold text-gray-300 mb-2">
                      Program URL / Identifier
                    </label>
                    <div className="relative">
                      <input
                        id="ingest-url"
                        type="text"
                        required
                        value={url}
                        onChange={(e) => setUrl(e.target.value)}
                        placeholder="https://bugcrowd.com/my-program"
                        className="block w-full bg-background-card/50 border border-white/10 rounded-lg px-4 py-3 text-white placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-transparent transition-all text-sm pr-32"
                      />
                      {detectedPlatform && (
                        <div className="absolute right-3 top-1/2 -translate-y-1/2">
                          <PlatformBadge platform={detectedPlatform} />
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Platform detection card */}
                  <AnimatePresence>
                    {detectedPlatform && detectedPlatform !== 'custom' && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="p-4 bg-primary/5 border border-primary/15 rounded-xl"
                      >
                        <div className="flex items-center justify-between">
                          <div>
                            <div className="text-xs text-gray-400">Detected Platform</div>
                            <div className="text-sm font-bold text-white capitalize mt-0.5">
                              {detectedPlatform === 'bugcrowd'
                                ? '🟡 Bugcrowd Engagement'
                                : '🔵 HackerOne Program'}
                            </div>
                            <div className="text-xs text-gray-500 mt-1">
                              {detectedPlatform === 'bugcrowd'
                                ? 'AI-assisted scraping + scope extraction will be activated'
                                : 'Program URL saved. Use API credentials for full scope sync.'}
                            </div>
                          </div>
                          <span className="text-[10px] bg-primary/20 text-primary px-2.5 py-1 rounded font-mono uppercase font-bold">
                            READY
                          </span>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>

                  {/* Custom scope fields */}
                  <AnimatePresence>
                    {detectedPlatform === 'custom' && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="space-y-4 border-t border-white/5 pt-4"
                      >
                        <div>
                          <label className="block text-sm font-semibold text-gray-300 mb-2">
                            Program Segment Name
                          </label>
                          <input
                            type="text"
                            required
                            value={customName}
                            onChange={(e) => setCustomName(e.target.value)}
                            placeholder="e.g. Internal Infrastructure"
                            className="block w-full bg-background-card/50 border border-white/10 rounded-lg px-4 py-3 text-white placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-primary/50 text-sm"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-semibold text-gray-300 mb-2">
                            Scope Lines (CSV/Domains)
                          </label>
                          <textarea
                            rows={3}
                            required
                            value={customScope}
                            onChange={(e) => setCustomScope(e.target.value)}
                            placeholder="*.example.com&#10;192.168.1.0/24"
                            className="block w-full bg-background-card/50 border border-white/10 rounded-lg px-4 py-3 text-white placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-primary/50 text-sm font-mono"
                          />
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>

                  <Button
                    id="btn-ingest-scope"
                    type="submit"
                    disabled={ingesting || !url}
                    className="w-full py-3 text-base"
                  >
                    {ingesting ? (
                      <span className="flex items-center justify-center gap-2">
                        <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                        Pipeline Running...
                      </span>
                    ) : (
                      'Initialize AI Scope Extraction'
                    )}
                  </Button>
                </form>
              </div>
            </div>

            {/* Pipeline Panel */}
            <div>
              <AnimatePresence>
                {pipelineVisible ? (
                  <IngestionPipelinePanel
                    platform={pipelinePlatform}
                    visible={pipelineVisible}
                    onComplete={handlePipelineComplete}
                    onError={handlePipelineError}
                    onClose={() => setPipelineVisible(false)}
                  />
                ) : (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="h-full flex flex-col items-center justify-center text-center p-12 border border-white/5 rounded-2xl bg-background-card/20"
                  >
                    <div className="text-5xl mb-4">🔄</div>
                    <h4 className="text-sm font-bold text-gray-300">Pipeline Ready</h4>
                    <p className="text-xs text-gray-600 mt-2 max-w-xs">
                      Paste a program URL and click Extract. The AI pipeline will stream
                      live stage-by-stage progress here in realtime.
                    </p>

                    {/* Flow diagram */}
                    <div className="mt-6 flex flex-col items-center gap-1 text-[10px] text-gray-600 font-mono">
                      {[
                        'URL Detection',
                        'Page Fetch',
                        'Scope Extraction',
                        'AI Validation',
                        'Target Normalization',
                        'Graph Generation',
                        'Monitoring Activation',
                        'Findings Pipeline',
                      ].map((stage, i) => (
                        <React.Fragment key={stage}>
                          <span className="px-3 py-1 bg-white/3 border border-white/5 rounded-md">
                            {stage}
                          </span>
                          {i < 7 && <span className="text-white/20">↓</span>}
                        </React.Fragment>
                      ))}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </motion.div>
        )}

        {/* ── Credentials Tab ── */}
        {activeTab === 'credentials' && (
          <motion.div
            key="credentials"
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -15 }}
            className="grid grid-cols-1 lg:grid-cols-2 gap-6"
          >
            {/* HackerOne API form */}
            <div className="relative group">
              <div className="absolute -inset-[1px] bg-gradient-to-r from-sky-500 to-primary rounded-2xl opacity-60 blur-sm" />
              <div className="relative glass-panel p-8 shadow-2xl rounded-2xl border border-white/10 bg-background-card/85">
                <div className="flex items-center gap-3 mb-2">
                  <span className="text-2xl">🔵</span>
                  <h3 className="text-xl font-bold text-white">HackerOne API Integration</h3>
                </div>
                <p className="text-xs text-gray-500 mb-6">
                  Connect your HackerOne API credentials to sync all accessible programs, scopes, and reports
                  with full realtime pipeline visibility.
                </p>

                <form onSubmit={handleCredentials} className="space-y-5">
                  <div>
                    <label className="block text-sm font-semibold text-gray-300 mb-2">
                      HackerOne Username / Handle
                    </label>
                    <input
                      id="h1-username"
                      type="text"
                      required
                      value={h1User}
                      onChange={(e) => setH1User(e.target.value)}
                      placeholder="e.g. operators-hq"
                      className="block w-full bg-background-card/50 border border-white/10 rounded-lg px-4 py-3 text-white placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-sky-500/50 text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-gray-300 mb-2">
                      HackerOne API Token
                    </label>
                    <input
                      id="h1-token"
                      type="password"
                      required
                      value={h1Token}
                      onChange={(e) => setH1Token(e.target.value)}
                      placeholder="••••••••••••••••••••"
                      className="block w-full bg-background-card/50 border border-white/10 rounded-lg px-4 py-3 text-white placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-sky-500/50 text-sm"
                    />
                  </div>

                  <div className="pt-2 border-t border-white/5 text-xs text-gray-600 space-y-1">
                    <p>✓ Validates credentials via HackerOne API</p>
                    <p>✓ Syncs all accessible programs & structured scopes</p>
                    <p>✓ Imports your submitted reports</p>
                    <p>✓ Streams realtime pipeline events</p>
                  </div>

                  <Button
                    id="btn-h1-sync"
                    type="submit"
                    disabled={credLoading}
                    className="w-full py-3 text-base"
                  >
                    {credLoading ? (
                      <span className="flex items-center justify-center gap-2">
                        <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                        Syncing Programs...
                      </span>
                    ) : (
                      'Connect & Sync All Programs'
                    )}
                  </Button>
                </form>
              </div>
            </div>

            {/* HackerOne pipeline status */}
            <div>
              <AnimatePresence>
                {pipelineVisible && pipelinePlatform === 'hackerone' ? (
                  <IngestionPipelinePanel
                    platform="hackerone"
                    visible={pipelineVisible && pipelinePlatform === 'hackerone'}
                    onComplete={handlePipelineComplete}
                    onError={handlePipelineError}
                    onClose={() => setPipelineVisible(false)}
                  />
                ) : (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="h-full flex flex-col items-center justify-center text-center p-12 border border-white/5 rounded-2xl bg-background-card/20"
                  >
                    <div className="text-5xl mb-4">🔵</div>
                    <h4 className="text-sm font-bold text-gray-300">HackerOne Sync Pipeline</h4>
                    <p className="text-xs text-gray-600 mt-2 max-w-xs">
                      Enter credentials and click Sync. Realtime pipeline progress will appear here:
                      programs fetched → scopes normalized → reports synced → complete.
                    </p>

                    <div className="mt-6 flex flex-col items-center gap-1 text-[10px] text-gray-600 font-mono">
                      {[
                        'Credential Validation',
                        'Programs Fetched',
                        'Scopes Normalized',
                        'Reports Synced',
                        'Sync Complete',
                      ].map((stage, i) => (
                        <React.Fragment key={stage}>
                          <span className="px-3 py-1 bg-white/3 border border-white/5 rounded-md">
                            {stage}
                          </span>
                          {i < 4 && <span className="text-white/20">↓</span>}
                        </React.Fragment>
                      ))}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default ProgramsPage
