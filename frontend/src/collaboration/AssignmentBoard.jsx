import React, { useMemo, useState } from 'react'

const progressMap = {
  open: 0,
  triaging: 20,
  validating: 55,
  reporting: 85,
  resolved: 100,
}

const statusTone = {
  open: 'border-white/10 bg-white/5 text-slate-200',
  triaging: 'border-cyan-400/20 bg-cyan-400/10 text-cyan-100',
  validating: 'border-amber-400/20 bg-amber-400/10 text-amber-100',
  reporting: 'border-fuchsia-400/20 bg-fuchsia-400/10 text-fuchsia-100',
  resolved: 'border-emerald-400/20 bg-emerald-400/10 text-emerald-100',
}

const AssignmentBoard = ({ investigation, assignment, investigations = [], onAssign }) => {
  const [assigneeId, setAssigneeId] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const currentStage = investigation?.workflow_stage || investigation?.status || 'open'
  const progress = progressMap[currentStage] ?? 0

  const recentInvestigations = useMemo(() => investigations.slice(0, 6), [investigations])

  const handleSubmit = async (event) => {
    event.preventDefault()
    if (!assigneeId.trim() || typeof onAssign !== 'function' || !investigation?.id) return
    setSubmitting(true)
    try {
      await onAssign({ assignee_id: assigneeId.trim() })
      setAssigneeId('')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className="rounded-3xl border border-white/10 bg-slate-950/70 p-5 shadow-[0_20px_80px_rgba(0,0,0,0.28)] backdrop-blur">
      <div className="flex items-start justify-between gap-4 border-b border-white/10 pb-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.3em] text-emerald-300">Assignment board</p>
          <h3 className="mt-2 text-xl font-semibold text-white">Ownership, escalation, and workflow visibility</h3>
        </div>
        <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${statusTone[currentStage] || statusTone.open}`}>
          {currentStage}
        </span>
      </div>

      <div className="mt-4 rounded-2xl border border-white/10 bg-slate-900/80 p-4">
        <div className="flex items-center justify-between text-sm text-slate-300">
          <span>Workflow progress</span>
          <span>{progress}%</span>
        </div>
        <div className="mt-3 h-2 rounded-full bg-white/10">
          <div className="h-2 rounded-full bg-gradient-to-r from-cyan-400 via-fuchsia-400 to-emerald-400" style={{ width: `${progress}%` }} />
        </div>
        <div className="mt-3 text-xs text-slate-400">
          Investigations typically move from triage to validation, reporting, and finally resolution once evidence is complete.
        </div>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
          <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">Current owner</div>
          <div className="mt-2 text-sm font-semibold text-white">
            {investigation?.assigned_to || assignment?.current?.assignee_id || 'Unassigned'}
          </div>
          <div className="mt-1 text-xs text-slate-400">
            {assignment?.current?.status || 'No active assignment'}
          </div>
        </div>
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
          <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">Resolution target</div>
          <div className="mt-2 text-sm font-semibold text-white">{investigation?.severity || 'medium'} priority</div>
          <div className="mt-1 text-xs text-slate-400">High-signal workflows should remain assigned until evidence is fully validated.</div>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="mt-4 rounded-2xl border border-white/10 bg-slate-900/80 p-4">
        <label className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">Reassign to analyst</label>
        <div className="mt-2 flex flex-col gap-3 sm:flex-row">
          <input
            value={assigneeId}
            onChange={(event) => setAssigneeId(event.target.value)}
            placeholder="Analyst user ID"
            className="flex-1 rounded-2xl border border-white/10 bg-slate-950/80 px-4 py-3 text-sm text-white outline-none placeholder:text-slate-500 focus:border-emerald-400/50"
          />
          <button
            type="submit"
            disabled={submitting || !assigneeId.trim()}
            className="rounded-full bg-emerald-400 px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-emerald-300 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {submitting ? 'Assigning...' : 'Assign'}
          </button>
        </div>
      </form>

      <div className="mt-5 grid gap-3">
        <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">Recent investigations</div>
        {recentInvestigations.length ? recentInvestigations.map((item) => (
          <div key={item.id} className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <div className="text-sm font-semibold text-white">{item.title}</div>
                <div className="mt-1 text-xs text-slate-400">{item.severity} · {item.status}</div>
              </div>
              <span className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold ${statusTone[item.workflow_stage] || statusTone.open}`}>
                {item.workflow_stage}
              </span>
            </div>
          </div>
        )) : (
          <div className="rounded-2xl border border-dashed border-white/10 bg-white/[0.02] p-5 text-sm text-slate-400">
            No active investigations yet.
          </div>
        )}
      </div>
    </section>
  )
}

export default AssignmentBoard
