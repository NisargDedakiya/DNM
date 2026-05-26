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

const EvidencePanel = ({ evidence = [], investigation, onUploadEvidence, onAttachEvidence }) => {
  const [fileName, setFileName] = useState('')
  const [description, setDescription] = useState('')
  const [evidenceType, setEvidenceType] = useState('screenshot')
  const [selectedFile, setSelectedFile] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  const previewUrl = useMemo(() => {
    if (!selectedFile) return null
    return URL.createObjectURL(selectedFile)
  }, [selectedFile])

  const handleSubmit = async (event) => {
    event.preventDefault()
    if (!description.trim() || typeof onUploadEvidence !== 'function') return
    setSubmitting(true)
    try {
      await onUploadEvidence({
        file_path: fileName || selectedFile?.name || `evidence-${Date.now()}`,
        description: description.trim(),
        evidence_type: evidenceType,
      })
      setFileName('')
      setDescription('')
      setEvidenceType('screenshot')
      setSelectedFile(null)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className="rounded-3xl border border-white/10 bg-slate-950/70 p-5 shadow-[0_20px_80px_rgba(0,0,0,0.28)] backdrop-blur">
      <div className="flex items-start justify-between gap-4 border-b border-white/10 pb-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.3em] text-fuchsia-300">Evidence panel</p>
          <h3 className="mt-2 text-xl font-semibold text-white">Artifacts, screenshots, logs, and notes</h3>
          <p className="mt-2 text-sm leading-6 text-slate-300">
            Evidence is versioned and org-isolated. Use descriptive filenames and keep uploads tied to the current investigation.
          </p>
        </div>
        <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-right text-xs text-slate-400">
          <div className="uppercase tracking-[0.24em]">Investigation</div>
          <div className="mt-1 text-sm font-semibold text-white">{investigation?.title || 'Unassigned'}</div>
        </div>
      </div>

      {previewUrl ? (
        <div className="mt-4 overflow-hidden rounded-2xl border border-white/10 bg-slate-900">
          <img src={previewUrl} alt="evidence preview" className="h-48 w-full object-cover" />
        </div>
      ) : null}

      <form onSubmit={handleSubmit} className="mt-4 grid gap-3 rounded-2xl border border-white/10 bg-slate-900/80 p-4">
        <div className="grid gap-3 md:grid-cols-3">
          <div className="md:col-span-2">
            <label className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">Evidence description</label>
            <input
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="What does this artifact prove?"
              className="mt-2 w-full rounded-2xl border border-white/10 bg-slate-950/80 px-4 py-3 text-sm text-white outline-none placeholder:text-slate-500 focus:border-fuchsia-400/50"
            />
          </div>
          <div>
            <label className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">Type</label>
            <select
              value={evidenceType}
              onChange={(event) => setEvidenceType(event.target.value)}
              className="mt-2 w-full rounded-2xl border border-white/10 bg-slate-950/80 px-4 py-3 text-sm text-white outline-none focus:border-fuchsia-400/50"
            >
              <option value="screenshot">Screenshot</option>
              <option value="log">Log</option>
              <option value="note">Note</option>
              <option value="request">Request</option>
              <option value="response">Response</option>
              <option value="code">Code</option>
            </select>
          </div>
        </div>

        <div className="grid gap-3 md:grid-cols-[1.5fr_1fr_auto] md:items-end">
          <div>
            <label className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">Browser-visible file label</label>
            <input
              value={fileName}
              onChange={(event) => setFileName(event.target.value)}
              placeholder="e.g. login-bypass-response.png"
              className="mt-2 w-full rounded-2xl border border-white/10 bg-slate-950/80 px-4 py-3 text-sm text-white outline-none placeholder:text-slate-500 focus:border-fuchsia-400/50"
            />
          </div>
          <div>
            <label className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">Preview file</label>
            <input
              type="file"
              onChange={(event) => setSelectedFile(event.target.files?.[0] || null)}
              className="mt-2 block w-full text-sm text-slate-300 file:mr-3 file:rounded-full file:border-0 file:bg-fuchsia-400 file:px-4 file:py-2 file:text-sm file:font-semibold file:text-slate-950 hover:file:bg-fuchsia-300"
            />
          </div>
          <button
            type="submit"
            disabled={submitting || !description.trim()}
            className="rounded-full bg-fuchsia-400 px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-fuchsia-300 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {submitting ? 'Uploading...' : 'Upload evidence'}
          </button>
        </div>
      </form>

      <div className="mt-5 space-y-3">
        {evidence.length ? evidence.map((item) => (
          <article key={item.id} className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <div className="text-sm font-semibold text-white">{item.description || item.file_path}</div>
                <div className="mt-1 text-xs text-slate-400">{item.evidence_type} · v{item.version} · {formatTime(item.created_at)}</div>
              </div>
              <div className="flex items-center gap-2 text-xs text-slate-400">
                <span className="rounded-full border border-white/10 bg-slate-900 px-2 py-1">{item.checksum ? item.checksum.slice(0, 12) : 'no checksum'}</span>
                {typeof onAttachEvidence === 'function' ? (
                  <button
                    type="button"
                    onClick={() => onAttachEvidence(item)}
                    className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-slate-200 transition hover:border-fuchsia-300/40 hover:bg-fuchsia-400/10"
                  >
                    Attach version
                  </button>
                ) : null}
              </div>
            </div>
          </article>
        )) : (
          <div className="rounded-2xl border border-dashed border-white/10 bg-white/[0.02] p-6 text-sm text-slate-400">
            No evidence has been uploaded yet. Add screenshots, logs, or notes as the investigation develops.
          </div>
        )}
      </div>
    </section>
  )
}

export default EvidencePanel
