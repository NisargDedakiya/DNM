import { create } from 'zustand';

const useFindingsStore = create((set) => ({
  findings: [],
  isLoading: false,
  filters: { severity: 'all', status: 'open' },
  
  setFindings: (findings) => set({ findings }),
  setLoading: (status) => set({ isLoading: status }),
  setFilters: (filters) => set((state) => ({ filters: { ...state.filters, ...filters } })),
  
  addFinding: (finding) => set((state) => ({ 
    findings: [finding, ...state.findings] 
  })),
  
  updateFinding: (id, updates) => set((state) => ({
    findings: state.findings.map(f => f.id === id ? { ...f, ...updates } : f)
  })),
}));

export default useFindingsStore;
