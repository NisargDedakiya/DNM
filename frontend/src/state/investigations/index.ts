import { create } from 'zustand'

export interface Investigation {
  id: string
  title: string
  status: 'active' | 'archived' | 'completed'
  created_at: string
  updated_at?: string
  findings_count: number
  creator_id: string
}

export interface Evidence {
  id: string
  investigation_id: string
  type: 'log' | 'screenshot' | 'payload' | 'pcap' | 'text'
  content: string
  metadata?: any
  created_at: string
}

export interface InvestigationsState {
  investigations: Investigation[]
  activeInvestigationId: string | null
  evidenceList: Evidence[]
  isLoading: boolean
  setInvestigations: (investigations: Investigation[]) => void
  setActiveInvestigationId: (id: string | null) => void
  setEvidenceList: (evidence: Evidence[]) => void
  addEvidence: (evidence: Evidence) => void
  setLoading: (status: boolean) => void
}

export const useInvestigationsStore = create<InvestigationsState>((set) => ({
  investigations: [],
  activeInvestigationId: null,
  evidenceList: [],
  isLoading: false,
  setInvestigations: (investigations) => set({ investigations }),
  setActiveInvestigationId: (id) => set({ activeInvestigationId: id }),
  setEvidenceList: (evidenceList) => set({ evidenceList }),
  addEvidence: (evidence) => set((state) => ({ evidenceList: [...state.evidenceList, evidence] })),
  setLoading: (status) => set({ isLoading: status }),
}))

export default useInvestigationsStore
