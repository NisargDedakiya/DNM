import { create } from 'zustand'

export interface Scan {
  id: string
  name: string
  target: string
  status: 'running' | 'completed' | 'failed' | 'scheduled'
  progress: number
  findings_count: number
  created_at: string
  updated_at?: string
}

export interface HealthMetric {
  service: string
  status: 'healthy' | 'unhealthy' | 'degraded'
  latency_ms: number
  message?: string
}

export interface MonitoringState {
  scans: Scan[]
  healthMetrics: HealthMetric[]
  isLoading: boolean
  setScans: (scans: Scan[]) => void
  addScan: (scan: Scan) => void
  updateScan: (id: string, updates: Partial<Scan>) => void
  setHealthMetrics: (metrics: HealthMetric[]) => void
  setLoading: (status: boolean) => void
}

export const useMonitoringStore = create<MonitoringState>((set) => ({
  scans: [],
  healthMetrics: [],
  isLoading: false,
  setScans: (scans) => set({ scans }),
  addScan: (scan) => set((state) => ({ scans: [scan, ...state.scans] })),
  updateScan: (id, updates) =>
    set((state) => ({
      scans: state.scans.map((s) => (s.id === id ? { ...s, ...updates } : s)),
    })),
  setHealthMetrics: (metrics) => set({ healthMetrics: metrics }),
  setLoading: (status) => set({ isLoading: status }),
}))

export default useMonitoringStore
