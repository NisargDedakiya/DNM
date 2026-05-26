import React from 'react'

const PrivilegeChainExplorer = ({ privilegeChain = null, authInheritance = null, loading = false }) => {
  const transitions = privilegeChain?.transitions || []
  const tokens = authInheritance?.trust_tokens || []

  return (
    <section className="rounded-3xl border border-white/10 bg-white/[0.03] p-5 text-white">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.35em] text-cyan-300">Privilege chains</p>
          <h3 className="mt-2 text-lg font-semibold">Auth inheritance and escalation reasoning</h3>
        </div>
        <div className="text-xs text-slate-400">{loading ? 'Tracing...' : `${transitions.length} transitions`}</div>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <div className="rounded-2xl border border-white/10 bg-slate-950/60 p-4">
          <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">Severity</div>
          <div className="mt-2 text-3xl font-semibold text-white">{privilegeChain?.severity || 'idle'}</div>
        </div>
        <div className="rounded-2xl border border-white/10 bg-slate-950/60 p-4">
          <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">Auth risk</div>
          <div className="mt-2 text-3xl font-semibold text-white">{authInheritance?.auth_inheritance_risk ?? 0}</div>
        </div>
        <div className="rounded-2xl border border-white/10 bg-slate-950/60 p-4">
          <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">Trust tokens</div>
          <div className="mt-2 text-3xl font-semibold text-white">{tokens.length}</div>
        </div>
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-2">
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
          <div className="text-sm font-semibold text-white">Privilege escalation path</div>
          <div className="mt-3 space-y-3">
            {transitions.length === 0 ? (
              <div className="rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-sm text-slate-400">No privilege chain available yet.</div>
            ) : transitions.map((step, index) => (
              <div key={`${step.role || index}-${index}`} className="rounded-xl border border-white/10 bg-black/20 px-3 py-2">
                <div className="text-sm font-medium text-white">{step.role || 'viewer'} → {step.target_role || step.escalated_privilege || 'unknown'}</div>
                <div className="mt-1 text-xs text-slate-400">Escalation {step.escalation ?? 0} · Permission {step.permission || 'n/a'}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
          <div className="text-sm font-semibold text-white">Trust relationship mapping</div>
          <div className="mt-3 space-y-3">
            {tokens.length === 0 ? (
              <div className="rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-sm text-slate-400">No auth trust tokens correlated.</div>
            ) : tokens.map((token, index) => (
              <div key={`${token.source || index}-${index}`} className="rounded-xl border border-white/10 bg-black/20 px-3 py-2">
                <div className="text-sm font-medium text-white">{token.source || 'source'} → {token.target || 'target'}</div>
                <div className="mt-1 text-xs text-slate-400">{token.token_type || 'jwt'} · Delegation {token.delegation ? 'yes' : 'no'}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}

export default PrivilegeChainExplorer