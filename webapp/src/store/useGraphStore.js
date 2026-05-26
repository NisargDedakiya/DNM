import { create } from 'zustand';

const useGraphStore = create((set) => ({
  nodes: [],
  edges: [],
  selectedNode: null,
  isLoading: false,
  
  setGraphData: (nodes, edges) => set({ nodes, edges }),
  setSelectedNode: (node) => set({ selectedNode: node }),
  setLoading: (status) => set({ isLoading: status }),
  
  updateNodeStatus: (nodeId, status) => set((state) => ({
    nodes: state.nodes.map(n => n.id === nodeId ? { ...n, data: { ...n.data, status } } : n)
  })),
}));

export default useGraphStore;
