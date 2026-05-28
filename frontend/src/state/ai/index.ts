import { create } from 'zustand'

export interface AIMessage {
  id?: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string
  isStreaming?: boolean
}

export interface Recommendation {
  id: string
  title: string
  description: string
  impact: 'low' | 'medium' | 'high'
  mitigation: string
  created_at: string
}

export interface AIState {
  messages: AIMessage[]
  isTyping: boolean
  recommendations: Recommendation[]
  addMessage: (msg: AIMessage) => void
  appendStreamChunk: (chunk: string) => void
  setTyping: (status: boolean) => void
  clearChat: () => void
  setRecommendations: (recs: Recommendation[]) => void
}

export const useAIStore = create<AIState>((set) => ({
  messages: [],
  isTyping: false,
  recommendations: [],
  addMessage: (msg) => set((state) => ({ messages: [...state.messages, msg] })),
  appendStreamChunk: (chunk) =>
    set((state) => {
      const lastMsg = state.messages[state.messages.length - 1]
      if (lastMsg && lastMsg.role === 'assistant' && lastMsg.isStreaming) {
        const updatedMsgs = [...state.messages]
        updatedMsgs[updatedMsgs.length - 1] = {
          ...lastMsg,
          content: lastMsg.content + chunk,
        }
        return { messages: updatedMsgs }
      }
      return state
    }),
  setTyping: (status) => set({ isTyping: status }),
  clearChat: () => set({ messages: [] }),
  setRecommendations: (recs) => set({ recommendations: recs }),
}))

export default useAIStore
