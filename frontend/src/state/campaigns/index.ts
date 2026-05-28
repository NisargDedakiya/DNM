import { create } from 'zustand'

export interface Campaign {
  id: string
  name: string
  description?: string
  status: 'active' | 'paused' | 'completed'
  playbook_id?: string
  target?: string
  created_at: string
}

export interface CampaignsState {
  campaigns: Campaign[]
  selectedCampaignId: string | null
  isLoading: boolean
  setCampaigns: (campaigns: Campaign[]) => void
  setSelectedCampaignId: (id: string | null) => void
  setLoading: (status: boolean) => void
}

export const useCampaignsStore = create<CampaignsState>((set) => ({
  campaigns: [],
  selectedCampaignId: null,
  isLoading: false,
  setCampaigns: (campaigns) => set({ campaigns }),
  setSelectedCampaignId: (id) => set({ selectedCampaignId: id }),
  setLoading: (status) => set({ isLoading: status }),
}))

export default useCampaignsStore
