import React, { useMemo, useState } from 'react'

const timeFormat = new Intl.DateTimeFormat(undefined, {
  month: 'short',
  day: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
})

const formatTime = (value) => {
  if (!value) return 'Just now'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? 'Just now' : timeFormat.format(date)
}

const MentionPill = ({ label }) => (
  <span className="inline-flex items-center rounded-full border border-cyan-400/20 bg-cyan-400/10 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-cyan-200">
    @{label}
  </span>
)

const InvestigationThread = ({ investigation, comments = [], summary, onComment, liveEvents = [], currentUserId }) => {
  const [draft, setDraft] = useState('')
  const [reasoning, setReasoning] = useState('')
  const [sending, setSending] = useState(false)

  const groupedComments = useMemo(() => comments || [], [comments])
  const threadEvents = liveEvents.filter((event) => String(event?.type || event?.event || '').includes('collaboration.'))

  const handleSubmit = async (event) => {
    event.preventDefault()
    if (!draft.trim() || typeof onComment !== 'function') return
    setSending(true)
    try {
      await onComment({ content: draft.trim(), ai_reasoning: reasoning.trim() || null })
      setDraft('')
      setReasoning('')
    } finally {
      setSending(false)
    }
  }

  return (
    <section className="rounded-3xl border border-white/10 bg-slate-950/70 p-5 shadow-[0_20px_80px_rgba(0,0,0,0.35)] backdrop-blur">
      <div className="flex items-start justify-between gap-4 border-b border-white/10 pb-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.3em] text-cyan-300">Investigation thread</p>
          <h2 className="mt-2 text-2xl font-semibold text-white">{investigation?.title || 'Select an investigation'}</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-300">
            {investigation?.summary || 'Shared discussion, analyst reasoning, and evidence notes stay scoped to this investigation.'}
          </p>
        </div>
        <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-right">
          <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">Current stage</div>
          <div className="mt-1 text-sm font-semibold text-white">{investigation?.workflow_stage || investigation?.status || 'open'}</div>
          <div className="mt-2 text-[11px] text-slate-400">{groupedComments.length} comments</div>
        </div>
      </div>

      {summary?.summary ? (
        <div className="mt-4 rounded-2xl border border-amber-400/20 bg-amber-400/10 p-4">
          <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-amber-200">AI reasoning summary</div>
          <p className="mt-2 text-sm leading-6 text-amber-50/90">{summary.summary}</p>
          {!!summary.open_questions?.length && (
            <div className="mt-3 flex flex-wrap gap-2">
              {summary.open_questions.slice(0, 4).map((item, index) => (
                <span key={`${item}-${index}`} className="rounded-full border border-amber-300/20 bg-black/20 px-3 py-1 text-xs text-amber-100">
                  {item}
                </span>
              ))}
            </div>
          )}
        </div>
      ) : null}

      <div className="mt-5 space-y-3">
        {groupedComments.length ? groupedComments.map((comment) => (
          <article key={comment.id} className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-cyan-400 to-blue-500 text-xs font-bold text-slate-950">
                  {(comment.author_id || 'A').slice(0, 2).toUpperCase()}
                </div>
                <div>
                  <div className="text-sm font-semibold text-white">
                    {comment.author_name || `Analyst ${String(comment.author_id || '').slice(0, 8)}`}
                    {currentUserId && comment.author_id === currentUserId ? <span className="ml-2 text-[11px] font-normal text-cyan-300">you</span> : null}
                  </div>
                  <div className="text-xs text-slate-400">{formatTime(comment.created_at)}</div>
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                {!!comment.mentions?.length && comment.mentions.map((mention) => <MentionPill key={`${comment.id}-${mention}`} label={mention} />)}
              </div>
            </div>
            <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-slate-200">{comment.content}</p>
            {comment.ai_reasoning ? (
              <div className="mt-3 rounded-2xl border border-cyan-400/20 bg-cyan-400/10 p-3 text-sm text-cyan-50/90">
                <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-cyan-200">AI reasoning</div>
                <p className="mt-2 whitespace-pre-wrap leading-6">{comment.ai_reasoning}</p>
              </div>
            ) : null}
            {Array.isArray(comment.children) && comment.children.length ? (
              <div className="mt-4 space-y-3 border-l border-white/10 pl-4">
                {comment.children.map((child) => (
                  <div key={child.id} className="rounded-xl border border-white/10 bg-slate-900/60 p-3">
                    <div className="text-xs text-slate-400">Reply by {child.author_name || `Analyst ${String(child.author_id || '').slice(0, 8)}`}</div>
                    <p className="mt-2 whitespace-pre-wrap text-sm text-slate-200">{child.content}</p>
                  </div>
                ))}
              </div>
            ) : null}
          </article>
        )) : (
          <div className="rounded-2xl border border-dashed border-white/10 bg-white/[0.02] p-8 text-center text-sm text-slate-400">
            No discussion yet. Open the thread with a concise analysis note, then attach evidence as the investigation evolves.
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} className="mt-5 space-y-3 rounded-2xl border border-white/10 bg-slate-900/80 p-4">
        <div>
          <label className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">Add comment</label>
          <textarea
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder="Share a finding, mention a teammate with @name, or note AI reasoning here..."
            className="mt-2 min-h-[96px] w-full rounded-2xl border border-white/10 bg-slate-950/80 px-4 py-3 text-sm text-white outline-none placeholder:text-slate-500 focus:border-cyan-400/50"
          />
        </div>
        <div>
          <label className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">AI reasoning attachment</label>
          <input
            value={reasoning}
            onChange={(event) => setReasoning(event.target.value)}
            placeholder="Optional AI-supported reasoning, validation note, or next-step suggestion"
            className="mt-2 w-full rounded-2xl border border-white/10 bg-slate-950/80 px-4 py-3 text-sm text-white outline-none placeholder:text-slate-500 focus:border-cyan-400/50"
          />
        </div>
        <div className="flex items-center justify-between gap-3">
          <div className="text-xs text-slate-500">
            Realtime updates from the org-scoped websocket bus are reflected in this thread.
          </div>
          <button
            type="submit"
            disabled={sending || !draft.trim()}
            className="rounded-full bg-cyan-400 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {sending ? 'Posting...' : 'Post comment'}
          </button>
        </div>
      </form>

      {threadEvents.length ? (
        <div className="mt-4 rounded-2xl border border-white/10 bg-white/[0.03] p-4">
          <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">Live collaboration feed</div>
          <div className="mt-3 space-y-2 text-sm text-slate-300">
            {threadEvents.slice(0, 3).map((event, index) => (
              <div key={`${event?.timestamp || index}-${index}`} className="rounded-xl border border-white/10 bg-slate-950/60 px-3 py-2">
                {String(event?.type || event?.event || 'update')}
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  )
}

export default InvestigationThread
