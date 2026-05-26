import React, { useMemo } from 'react'
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, Cell } from 'recharts'

const GraphPerformancePanel = ({ overview = null, graph = null, queues = null }) => {
  const nodeCount = Number(graph?.graph?.node_count || overview?.overview?.graph?.node_count || 0)
  const edgeCount = Number(graph?.graph?.edge_count || overview?.overview?.graph?.edge_count || 0)
  const nodeDensity = Number(graph?.graph?.node_density || overview?.overview?.graph?.node_density || 0)
  const renderBudget = Number(graph?.graph?.render_budget || overview?.overview?.graph?.render_budget || 0)

  const metrics = useMemo(() => ([
    { name: 'Nodes', value: nodeCount, tone: '#22d3ee' },
    { name: 'Edges', value: edgeCount, tone: '#a855f7' },
    { name: 'Density', value: Math.round(nodeDensity * 100), tone: '#f59e0b' },
    { name: 'Budget', value: renderBudget, tone: '#22c55e' },
  ]), [nodeCount, edgeCount, nodeDensity, renderBudget])

  const recommendations = graph?.graph?.recommendations || [
    'Prioritize high-signal nodes and defer low-value branches.',
    'Collapse dense subgraphs to reduce render cost.',
    'Cache graph snapshots for identical org-scoped attack paths.',
  ]

  return (
    <section className="rounded-3xl border border-white/10 bg-white/[0.03] p-5">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold text-white">Graph performance</h3>
          <p className="text-sm text-slate-400">Graph rendering metrics, node density, and attack graph optimization insights.</p>
        </div>
        <div className="text-xs text-slate-500">Queue pressure: {Math.round((queues?.queue_pressure?.backlog_pressure || 0) * 100)}%</div>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-4">
        {metrics.map((metric) => (
          <div key={metric.name} className="rounded-2xl border border-white/10 bg-slate-950/50 p-4">
            <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">{metric.name}</div>
            <div className="mt-2 text-2xl font-semibold text-white">{metric.value}</div>
          </div>
        ))}
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-2">
        <div className="rounded-2xl border border-white/10 bg-slate-950/50 p-4">
          <div className="text-sm font-semibold text-white">Graph render load</div>
          <div className="mt-4 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={metrics} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" horizontal={false} />
                <XAxis type="number" stroke="rgba(255,255,255,0.4)" />
                <YAxis dataKey="name" type="category" stroke="rgba(255,255,255,0.4)" width={80} />
                <Tooltip contentStyle={{ backgroundColor: '#0b1020', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '12px', color: '#fff' }} />
                <Bar dataKey="value" radius={[0, 8, 8, 0]}>
                  {metrics.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.tone} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-2xl border border-white/10 bg-slate-950/50 p-4">
          <div className="text-sm font-semibold text-white">Optimization insights</div>
          <div className="mt-3 space-y-2 text-sm text-slate-300">
            {recommendations.map((item) => (
              <div key={item} className="rounded-xl border border-white/10 bg-black/20 px-3 py-2">{item}</div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}

export default GraphPerformancePanel
