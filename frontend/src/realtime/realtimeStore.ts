import { create } from 'zustand'

export interface OptimisticUpdate {
  id: string
  domain: string
  originalState: any
  updatedState: any
  timestamp: number
}

export interface RealtimeState {
  isConnected: boolean
  activeAlerts: any[]
  recentEvents: any[]
  processedEventIds: string[]
  optimisticUpdates: OptimisticUpdate[]
  
  setConnected: (status: boolean) => void
  addAlert: (alert: any) => boolean  // Returns false if duplicate
  addEvent: (event: any) => boolean  // Returns false if duplicate
  clearAlerts: () => void
  
  // Optimistic updates
  registerOptimisticUpdate: (update: OptimisticUpdate) => void
  commitOptimisticUpdate: (id: string) => void
  rollbackOptimisticUpdate: (id: string) => void
}

export const useRealtimeStore = create<RealtimeState>((set, get) => ({
  isConnected: false,
  activeAlerts: [],
  recentEvents: [],
  processedEventIds: [],
  optimisticUpdates: [],

  setConnected: (status) => set({ isConnected: status }),

  addAlert: (alert) => {
    const id = alert.id || alert.event_id || alert.correlation_id
    if (id) {
      const processed = get().processedEventIds
      if (processed.includes(id)) {
        console.warn(`[RealtimeStore] Duplicate alert ignored: ${id}`)
        return false
      }
      set((state) => ({
        processedEventIds: [id, ...state.processedEventIds].slice(0, 200)
      }))
    }
    
    set((state) => ({
      activeAlerts: [alert, ...state.activeAlerts].slice(0, 50)
    }))
    return true
  },

  addEvent: (event) => {
    const id = event.event_id || event.id || event.correlation_id
    if (id) {
      const processed = get().processedEventIds
      if (processed.includes(id)) {
        console.warn(`[RealtimeStore] Duplicate event ignored: ${id}`)
        return false
      }
      set((state) => ({
        processedEventIds: [id, ...state.processedEventIds].slice(0, 200)
      }))
    }

    set((state) => ({
      recentEvents: [event, ...state.recentEvents].slice(0, 100)
    }))
    return true
  },

  clearAlerts: () => set({ activeAlerts: [] }),

  registerOptimisticUpdate: (update) => set((state) => ({
    optimisticUpdates: [...state.optimisticUpdates, update]
  })),

  commitOptimisticUpdate: (id) => set((state) => ({
    optimisticUpdates: state.optimisticUpdates.filter((u) => u.id !== id)
  })),

  rollbackOptimisticUpdate: (id) => set((state) => ({
    optimisticUpdates: state.optimisticUpdates.filter((u) => u.id !== id)
  }))
}))

export default useRealtimeStore
