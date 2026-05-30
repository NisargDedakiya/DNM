import { create } from 'zustand'

export interface SystemMetric {
  name: string
  value: number
  unit: string
  status: 'nominal' | 'warning' | 'critical'
  timestamp: string
}

export interface TelemetryTrace {
  id: string
  service: string
  durationMs: number
  path: string
  status: number
  timestamp: string
}

export interface WorkerStatus {
  id: string
  name: string
  status: 'idle' | 'busy' | 'offline'
  jobsCompleted: number
  lastHeartbeat: string
}

export interface TelemetryState {
  metrics: SystemMetric[]
  traces: TelemetryTrace[]
  workers: WorkerStatus[]
  isLoading: boolean
  
  setMetrics: (metrics: SystemMetric[]) => void
  addMetric: (metric: SystemMetric) => void
  setTraces: (traces: TelemetryTrace[]) => void
  addTrace: (trace: TelemetryTrace) => void
  setWorkers: (workers: WorkerStatus[]) => void
  updateWorker: (id: string, updates: Partial<WorkerStatus>) => void
  setLoading: (status: boolean) => void
  clearTelemetry: () => void
}

export const useTelemetryStore = create<TelemetryState>((set) => ({
  metrics: [],
  traces: [],
  workers: [],
  isLoading: false,

  setMetrics: (metrics) => set({ metrics }),
  addMetric: (metric) => set((state) => {
    // Keep only the last 50 samples of the same metric name to avoid memory bloat
    const filtered = state.metrics.filter((m) => !(m.name === metric.name && m.timestamp === metric.timestamp))
    return { metrics: [metric, ...filtered].slice(0, 100) }
  }),
  setTraces: (traces) => set({ traces }),
  addTrace: (trace) => set((state) => ({
    traces: [trace, ...state.traces].slice(0, 100)
  })),
  setWorkers: (workers) => set({ workers }),
  updateWorker: (id, updates) => set((state) => ({
    workers: state.workers.map((w) => (w.id === id ? { ...w, ...updates } : w))
  })),
  setLoading: (status) => set({ isLoading: status }),
  clearTelemetry: () => set({ metrics: [], traces: [], workers: [] })
}))

export default useTelemetryStore
