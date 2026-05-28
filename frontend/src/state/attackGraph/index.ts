import { create } from 'zustand'

export interface GraphNode {
  id: string
  type: string
  label: string
  data: {
    status?: string
    severity?: string
    [key: string]: any
  }
  position?: { x: number; y: number }
  [key: string]: any
}

export interface GraphEdge {
  id: string
  source: string
  target: string
  type?: string
  [key: string]: any
}

export interface AttackGraphState {
  nodes: GraphNode[]
  edges: GraphEdge[]
  selectedNode: GraphNode | null
  isLoading: boolean
  setGraphData: (nodes: GraphNode[], edges: GraphEdge[]) => void
  setSelectedNode: (node: GraphNode | null) => void
  setLoading: (status: boolean) => void
  updateNodeStatus: (nodeId: string, status: string) => void
}

export const useAttackGraphStore = create<AttackGraphState>((set) => ({
  nodes: [],
  edges: [],
  selectedNode: null,
  isLoading: false,
  setGraphData: (nodes, edges) => set({ nodes, edges }),
  setSelectedNode: (node) => set({ selectedNode: node }),
  setLoading: (status) => set({ isLoading: status }),
  updateNodeStatus: (nodeId, status) =>
    set((state) => ({
      nodes: state.nodes.map((n) => (n.id === nodeId ? { ...n, data: { ...n.data, status } } : n)),
    })),
}))

export default useAttackGraphStore
