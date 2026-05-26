import { create } from 'zustand';

const useRealtimeStore = create((set) => ({
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
}));

export default useRealtimeStore;
