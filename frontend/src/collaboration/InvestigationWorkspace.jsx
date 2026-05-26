import React, { useEffect, useMemo, useRef, useState } from 'react'
import api from '../api/client'
import useAuthStore from '../stores/authStore'
import useRealtimeStore from '../store/useRealtimeStore'
import InvestigationThread from './InvestigationThread'
import EvidencePanel from './EvidencePanel'
import AssignmentBoard from './AssignmentBoard'

const formatNumber = (value) => new Intl.NumberFormat().format(value || 0)

const InvestigationWorkspace = ({ organizationId: organizationIdProp = null, attackGraphSummary = null }) => {
  const currentUser = useAuthStore((state) => state.user)
  const recentEvents = useRealtimeStore((state) => state.recentEvents)
  const organizationId = organizationIdProp || currentUser?.organization_id || localStorage.getItem('org_id') || ''

  const [investigations, setInvestigations] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [workspace, setWorkspace] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [creating, setCreating] = useState(false)
  const [draft, setDraft] = useState({ title: '', severity: 'high', summary: '' })
  const lastEventRef = useRef('')

  const selectedInvestigation = useMemo(() => {
    return workspace?.investigation || investigations.find((item) => item.id === selectedId) || null
  }, [workspace, investigations, selectedId])

  const loadInvestigations = async () => {
    if (!organizationId) return
    setLoading(true)
    try {
      const response = await api.get('/collaboration/investigations', {
        params: { organization_id: organizationId },
      })
      const items = response.data || []
      setInvestigations(items)
      if (!selectedId && items.length) {
        setSelectedId(items[0].id)
      }
      setError('')
    } catch (err) {
      setError(err?.response?.data?.detail || err?.message || 'Failed to load investigations')
    } finally {
      setLoading(false)
    }
  }

  const loadWorkspace = async (investigationId) => {
    if (!organizationId || !investigationId) return
    setLoading(true)
    try {
      const response = await api.get(`/collaboration/investigation/${investigationId}`, {
        params: { organization_id: organizationId },
      })
      setWorkspace(response.data)
      setError('')
    } catch (err) {
      setError(err?.response?.data?.detail || err?.message || 'Failed to load collaboration workspace')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadInvestigations()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [organizationId])

  useEffect(() => {
    if (selectedId) {
      loadWorkspace(selectedId)
    } else {
      setWorkspace(null)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId, organizationId])

  useEffect(() => {
    const latest = recentEvents?.[0]
    if (!latest) return
    const signature = `${latest.timestamp || ''}:${latest.type || latest.event || ''}`
    if (signature === lastEventRef.current) return
    lastEventRef.current = signature

    const eventType = String(latest.type || latest.event || '')
    if (!eventType.startsWith('collaboration.')) return
    loadInvestigations()
    if (selectedId) {
      loadWorkspace(selectedId)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [recentEvents, selectedId, organizationId])

  const createWorkspace = async (event) => {
    event.preventDefault()
    if (!draft.title.trim() || !organizationId) return
    setCreating(true)
    try {
      const response = await api.post('/collaboration/investigation', {
        organization_id: organizationId,
        title: draft.title.trim(),
        severity: draft.severity,
        summary: draft.summary.trim() || null,
      })
      const created = response.data?.investigation || response.data?.thread?.investigation
      await loadInvestigations()
      if (created?.id) {
        setSelectedId(created.id)
        setWorkspace(response.data)
      }
      setDraft({ title: '', severity: 'high', summary: '' })
    } catch (err) {
      setError(err?.response?.data?.detail || err?.message || 'Failed to create investigation workspace')
    } finally {
      setCreating(false)
    }
  }

  const addComment = async ({ content, ai_reasoning }) => {
    if (!selectedId) return
    const response = await api.post('/collaboration/comment', {
      organization_id: organizationId,
      investigation_id: selectedId,
      content,
      ai_reasoning,
    })
    await loadWorkspace(selectedId)
    return response.data
  }

  const assignInvestigation = async ({ assignee_id }) => {
    if (!selectedId) return
    const response = await api.post('/collaboration/assign', {
      organization_id: organizationId,
      investigation_id: selectedId,
      assignee_id,
    })
    await loadWorkspace(selectedId)
    return response.data
  }

  const uploadEvidence = async ({ file_path, description, evidence_type }) => {
    if (!selectedId) return
    const response = await api.post('/collaboration/evidence', {
      organization_id: organizationId,
      investigation_id: selectedId,
      file_path,
      description,
      evidence_type,
    })
    await loadWorkspace(selectedId)
    return response.data
  }

  const attachEvidence = async (item) => {
    if (!selectedId || !item?.id) return
    const response = await api.post('/collaboration/evidence/attach', {
      organization_id: organizationId,
      investigation_id: selectedId,
      evidence_id: item.id,
      description: `${item.description || item.file_path} - attached version`,
    })
    await loadWorkspace(selectedId)
    return response.data
  }

  const liveCollaborationEvents = recentEvents.filter((event) => String(event?.type || event?.event || '').startsWith('collaboration.'))

  return (
    <div className="space-y-6">
      <section className="rounded-[2rem] border border-white/10 bg-gradient-to-br from-slate-950 via-slate-950 to-slate-900 p-6 shadow-[0_30px_100px_rgba(0,0,0,0.35)]">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.35em] text-cyan-300">Team collaboration</p>
            <h1 className="mt-3 text-3xl font-semibold text-white md:text-4xl">Shared investigation workspace</h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-300">
              Keep high-signal findings, evidence, analyst comments, and assignments in one org-isolated investigation flow.
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3">
              <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">Investigations</div>
              <div className="mt-1 text-2xl font-semibold text-white">{formatNumber(investigations.length)}</div>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3">
              <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">Live events</div>
              <div className="mt-1 text-2xl font-semibold text-white">{formatNumber(liveCollaborationEvents.length)}</div>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3">
              <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">Graph signals</div>
              <div className="mt-1 text-2xl font-semibold text-white">{attackGraphSummary?.nodes || attackGraphSummary?.edges || '—'}</div>
            </div>
          </div>
        </div>

        <form onSubmit={createWorkspace} className="mt-6 grid gap-3 rounded-3xl border border-white/10 bg-white/[0.03] p-4 lg:grid-cols-[1.4fr_0.7fr_1.2fr_auto] lg:items-end">
          <div>
            <label className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">Workspace title</label>
            <input
              value={draft.title}
              onChange={(event) => setDraft((state) => ({ ...state, title: event.target.value }))}
              placeholder="P1 auth bypass, attack chain, or cloud exposure"
              className="mt-2 w-full rounded-2xl border border-white/10 bg-slate-950/80 px-4 py-3 text-sm text-white outline-none placeholder:text-slate-500 focus:border-cyan-400/50"
            />
          </div>
          <div>
            <label className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">Severity</label>
            <select
              value={draft.severity}
              onChange={(event) => setDraft((state) => ({ ...state, severity: event.target.value }))}
              className="mt-2 w-full rounded-2xl border border-white/10 bg-slate-950/80 px-4 py-3 text-sm text-white outline-none focus:border-cyan-400/50"
            >
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </div>
          <div>
            <label className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">Context note</label>
            <input
              value={draft.summary}
              onChange={(event) => setDraft((state) => ({ ...state, summary: event.target.value }))}
              placeholder="Why is this worth team attention?"
              className="mt-2 w-full rounded-2xl border border-white/10 bg-slate-950/80 px-4 py-3 text-sm text-white outline-none placeholder:text-slate-500 focus:border-cyan-400/50"
            />
          </div>
          <button
            type="submit"
            disabled={creating || !draft.title.trim()}
            className="rounded-full bg-cyan-400 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {creating ? 'Creating...' : 'Create workspace'}
          </button>
        </form>
      </section>

      {error ? (
        <div className="rounded-2xl border border-red-400/20 bg-red-400/10 px-4 py-3 text-sm text-red-100">{error}</div>
      ) : null}

      <div className="grid gap-6 xl:grid-cols-[340px_minmax(0,1fr)]">
        <aside className="rounded-3xl border border-white/10 bg-slate-950/70 p-4 backdrop-blur">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold uppercase tracking-[0.24em] text-slate-400">Investigation list</h2>
            {loading ? <span className="text-xs text-slate-500">Syncing...</span> : null}
          </div>
          <div className="space-y-3">
            {investigations.length ? investigations.map((item) => (
              <button
                type="button"
                key={item.id}
                onClick={() => setSelectedId(item.id)}
                className={`w-full rounded-2xl border p-4 text-left transition ${selectedId === item.id ? 'border-cyan-400/40 bg-cyan-400/10' : 'border-white/10 bg-white/[0.03] hover:border-white/20'}`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="text-sm font-semibold text-white">{item.title}</div>
                    <div className="mt-1 text-xs text-slate-400">{item.severity} · {item.status}</div>
                  </div>
                  <span className="rounded-full border border-white/10 bg-white/5 px-2 py-1 text-[11px] font-semibold text-slate-200">
                    {item.workflow_stage}
                  </span>
                </div>
                {item.summary ? <p className="mt-3 line-clamp-3 text-xs leading-5 text-slate-400">{item.summary}</p> : null}
              </button>
            )) : (
              <div className="rounded-2xl border border-dashed border-white/10 bg-white/[0.02] p-5 text-sm text-slate-400">
                No investigations loaded yet. Create the first workspace for a high-signal finding or attack chain.
              </div>
            )}
          </div>
        </aside>

        <div className="space-y-6">
          <div className="rounded-3xl border border-white/10 bg-slate-950/70 p-5 backdrop-blur">
            <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">Workspace overview</div>
                <h2 className="mt-2 text-2xl font-semibold text-white">{selectedInvestigation?.title || 'Select an investigation'}</h2>
                <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-300">
                  {selectedInvestigation?.summary || 'Choose a workspace to review thread activity, evidence integrity, and analyst ownership.'}
                </p>
              </div>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <div className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3">
                  <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">Status</div>
                  <div className="mt-1 text-sm font-semibold text-white">{selectedInvestigation?.status || 'open'}</div>
                </div>
                <div className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3">
                  <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">Severity</div>
                  <div className="mt-1 text-sm font-semibold text-white">{selectedInvestigation?.severity || 'medium'}</div>
                </div>
                <div className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3">
                  <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">Assigned to</div>
                  <div className="mt-1 text-sm font-semibold text-white">{selectedInvestigation?.assigned_to || 'Unassigned'}</div>
                </div>
                <div className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3">
                  <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">Source finding</div>
                  <div className="mt-1 text-sm font-semibold text-white">{selectedInvestigation?.source_finding_id || 'N/A'}</div>
                </div>
              </div>
            </div>

            {attackGraphSummary ? (
              <div className="mt-4 rounded-2xl border border-cyan-400/20 bg-cyan-400/10 p-4 text-sm text-cyan-50">
                <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-cyan-200">Attack graph integration</div>
                <p className="mt-2 leading-6">
                  {attackGraphSummary.summary || 'Graph intelligence is available for this workspace and should be reviewed alongside evidence and analyst notes.'}
                </p>
              </div>
            ) : null}
          </div>

          <div className="grid gap-6 2xl:grid-cols-2">
            <InvestigationThread
              investigation={workspace?.investigation || selectedInvestigation}
              comments={workspace?.thread?.comments || []}
              summary={workspace?.thread?.summary}
              onComment={addComment}
              liveEvents={liveCollaborationEvents}
              currentUserId={currentUser?.id}
            />
            <EvidencePanel
              investigation={workspace?.investigation || selectedInvestigation}
              evidence={workspace?.evidence || []}
              onUploadEvidence={uploadEvidence}
              onAttachEvidence={attachEvidence}
            />
          </div>

          <AssignmentBoard
            investigation={workspace?.investigation || selectedInvestigation}
            assignment={workspace?.assignment}
            investigations={investigations}
            onAssign={assignInvestigation}
          />
        </div>
      </div>
    </div>
  )
}

export default InvestigationWorkspace
