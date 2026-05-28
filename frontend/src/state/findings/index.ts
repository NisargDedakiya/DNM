import { create } from 'zustand'

export interface Finding {
  id: string
  title: string
  description?: string
  severity: 'low' | 'medium' | 'high' | 'critical'
  status: 'open' | 'triaged' | 'resolved' | 'false_positive'
  asset_id?: string
  organization_id: string
  created_at: string
  updated_at?: string
  [key: string]: any
}

export interface FindingsFilters {
  severity: string
  status: string
  query: string
}

export interface FindingsState {
  findings: Finding[]
  isLoading: boolean
  filters: FindingsFilters
  selectedFindingId: string | null
  setFindings: (findings: Finding[]) => void
  setLoading: (status: boolean) => void
  addFinding: (finding: Finding) => void
  updateFinding: (id: string, updates: Partial<Finding>) => void
  setFilters: (filters: Partial<FindingsFilters>) => void
  setSelectedFindingId: (id: string | null) => void
}

export const useFindingsStore = create<FindingsState>((set) => ({
  findings: [],
  isLoading: false,
  filters: { severity: 'all', status: 'open', query: '' },
  selectedFindingId: null,
  setFindings: (findings) => set({ findings }),
  setLoading: (status) => set({ isLoading: status }),
  addFinding: (finding) => set((state) => ({ findings: [finding, ...state.findings] })),
  updateFinding: (id, updates) =>
    set((state) => ({
      findings: state.findings.map((f) => (f.id === id ? { ...f, ...updates } : f)),
    })),
  setFilters: (filters) => set((state) => ({ filters: { ...state.filters, ...filters } })),
  setSelectedFindingId: (id) => set({ selectedFindingId: id }),
}))

export default useFindingsStore
