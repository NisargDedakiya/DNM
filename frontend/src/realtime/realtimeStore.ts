import { create } from 'zustand'

export interface RealtimeState {
  isConnected: boolean
  activeAlerts: any[]
  recentEvents: any[]
  setConnected: (status: boolean) => void
  addAlert: (alert: any) => void
  addEvent: (event: any) => void
  clearAlerts: () => void
}

export const useRealtimeStore = create<RealtimeState>((set) => ({
  isConnected: false,
  activeAlerts: [],
  recentEvents: [],
  setConnected: (status) => set({ isConnected: status }),
  addAlert: (alert) => set((state) => ({
    activeAlerts: [alert, ...state.activeAlerts].slice(0, 50)
  })),
  addEvent: (event) => set((state) => ({
    recentEvents: [event, ...state.recentEvents].slice(0, 100)
  })),
  clearAlerts: () => set({ activeAlerts: [] }),
}))

export default useRealtimeStore
