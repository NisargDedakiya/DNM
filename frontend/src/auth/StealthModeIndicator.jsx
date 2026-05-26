import React from 'react'

const StealthModeIndicator = ({ active = false, workspaceName = '', warning = 'Hidden investigations are org-scoped and access-controlled.' }) => {
  return (
    <div className={`rounded-2xl border px-4 py-3 text-sm ${active ? 'border-amber-400/20 bg-amber-400/10 text-amber-100' : 'border-emerald-400/20 bg-emerald-400/10 text-emerald-100'}`}>
      <div className="flex items-center justify-between gap-3">
        <span className="font-semibold">{active ? 'Stealth mode enabled' : 'Stealth mode disabled'}</span>
        <span className="text-xs uppercase tracking-[0.24em] opacity-80">{workspaceName || 'Workspace'}</span>
      </div>
      <p className="mt-2 text-xs opacity-80">{warning}</p>
    </div>
  )
}

export default StealthModeIndicator
