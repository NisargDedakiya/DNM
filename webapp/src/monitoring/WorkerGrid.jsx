import React, { useEffect, useMemo, useState } from 'react'
import api from '../api/client'

const toneForHealth = (score) => {
  if (score >= 0.85) return 'bg-emerald-400/10 border-emerald-400/20 text-emerald-100'
  if (score >= 0.7) return 'bg-cyan-400/10 border-cyan-400/20 text-cyan-100'
  if (score >= 0.5) return 'bg-amber-400/10 border-amber-400/20 text-amber-100'
  return 'bg-red-400/10 border-red-400/20 text-red-100'
}

const WorkerGrid = ({ organizationId, healthSnapshot = null }) => {
  const [payload, setPayload] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let mounted = true

    const load = async () => {
      if (!organizationId) return
      try {
        const response = await api.get('/monitoring/workers', { params: { organization_id: organizationId } })
        if (mounted) {
          setPayload(response.data)
          setError('')
        }
      } catch (err) {
        if (mounted) setError(err?.response?.data?.detail || err?.message || 'Failed to load workers')
      }
    }

    load()
    const interval = window.setInterval(load, 12000)
    return () => {
      mounted = false
      window.clearInterval(interval)
    }
  }, [organizationId])

  const workers = useMemo(() => payload?.workers || healthSnapshot?.workers?.workers || [], [payload, healthSnapshot])

  return (
    <section className="rounded-3xl border border-white/10 bg-white/[0.03] p-5">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold text-white">Worker grid</h3>
          <p className="text-sm text-slate-400">Realtime distributed worker load and health indicators.</p>
        </div>
        <div className="text-xs text-slate-500">{workers.length} workers</div>
      </div>

      {error ? <div className="mt-4 rounded-2xl border border-red-400/20 bg-red-400/10 px-4 py-3 text-sm text-red-100">{error}</div> : null}

      <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {workers.length ? workers.map((worker) => {
          const healthScore = Number(worker.health_score || 0)
          const load = Number(worker.current_load || 0)
          return (
            <article key={worker.id || worker.worker_id} className={`rounded-2xl border p-4 ${toneForHealth(healthScore)}`}>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="text-sm font-semibold text-white">{worker.region || 'global'} · {worker.status || 'idle'}</div>
                  <div className="mt-1 text-xs opacity-80">{worker.id || worker.worker_id}</div>
                </div>
                <div className="text-right text-xs uppercase tracking-[0.24em] opacity-80">{Math.round(healthScore * 100)}%</div>
              </div>
              <div className="mt-4 h-2 rounded-full bg-black/20">
                <div className="h-2 rounded-full bg-white/70" style={{ width: `${Math.min(100, load * 10)}%` }} />
              </div>
              <div className="mt-3 flex items-center justify-between text-xs opacity-85">
                <span>Load {load}</span>
                <span>Heartbeat {worker.last_heartbeat ? 'fresh' : 'unknown'}</span>
              </div>
            </article>
          )
        }) : (
          <div className="rounded-2xl border border-dashed border-white/10 bg-white/[0.02] p-6 text-sm text-slate-400">
            No workers reported yet.
          </div>
        )}
      </div>
    </section>
  )
}

export default WorkerGrid
