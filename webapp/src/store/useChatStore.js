import { create } from 'zustand';

const useChatStore = create((set) => ({
  messages: [],
  sessionId: null,
  isTyping: false,
  isOpen: false,
  
  setSessionId: (id) => set({ sessionId: id }),
  setOpen: (isOpen) => set({ isOpen }),
  setTyping: (status) => set({ isTyping: status }),
  
  addMessage: (msg) => set((state) => ({ 
    messages: [...state.messages, msg] 
  })),
  
  appendStreamChunk: (chunk) => set((state) => {
    const lastMsg = state.messages[state.messages.length - 1];
    if (lastMsg && lastMsg.role === 'assistant' && lastMsg.isStreaming) {
      const updatedMsgs = [...state.messages];
      updatedMsgs[updatedMsgs.length - 1] = {
        ...lastMsg,
        content: lastMsg.content + chunk
      };
      return { messages: updatedMsgs };
    }
    return state;
  }),
  
  clearChat: () => set({ messages: [], sessionId: null }),
}));

export default useChatStore;
