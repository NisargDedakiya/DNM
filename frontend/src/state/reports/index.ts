import { create } from 'zustand'

export interface Report {
  id: string
  title: string
  type: 'executive' | 'technical' | 'summary'
  status: 'pending' | 'completed' | 'failed'
  findingsCount: number
  downloadUrl?: string
  organizationId: string
  createdAt: string
  updatedAt?: string
}

export interface ReportsState {
  reports: Report[]
  selectedReportId: string | null
  isLoading: boolean
  
  setReports: (reports: Report[]) => void
  addReport: (report: Report) => void
  updateReport: (id: string, updates: Partial<Report>) => void
  setSelectedReportId: (id: string | null) => void
  setLoading: (status: boolean) => void
  clearReports: () => void
}

export const useReportsStore = create<ReportsState>((set) => ({
  reports: [],
  selectedReportId: null,
  isLoading: false,

  setReports: (reports) => set({ reports }),
  addReport: (report) => set((state) => ({ reports: [report, ...state.reports] })),
  updateReport: (id, updates) => set((state) => ({
    reports: state.reports.map((r) => (r.id === id ? { ...r, ...updates } : r))
  })),
  setSelectedReportId: (id) => set({ selectedReportId: id }),
  setLoading: (status) => set({ isLoading: status }),
  clearReports: () => set({ reports: [], selectedReportId: null })
}))

export default useReportsStore
