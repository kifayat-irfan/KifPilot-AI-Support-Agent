import { create } from 'zustand'
import type { ChatSession, ChatMessage, Citation, StreamEvent } from '@/types'

interface ChatState {
  sessions: ChatSession[]
  currentSession: ChatSession | null
  messages: ChatMessage[]
  isStreaming: boolean
  isLoading: boolean
  error: string | null
  abortController: AbortController | null
  setSessions: (sessions: ChatSession[]) => void
  setCurrentSession: (session: ChatSession | null) => void
  addSession: (session: ChatSession) => void
  updateSession: (session: ChatSession) => void
  removeSession: (id: string) => void
  setMessages: (messages: ChatMessage[] | ((prev: ChatMessage[]) => ChatMessage[])) => void
  addMessage: (message: ChatMessage) => void
  updateMessage: (id: string, updates: Partial<ChatMessage>) => void
  clearMessages: () => void
  setStreaming: (streaming: boolean) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  setAbortController: (controller: AbortController | null) => void
  abortStream: () => void
}

export const useChatStore = create<ChatState>((set, get) => ({
  sessions: [],
  currentSession: null,
  messages: [],
  isStreaming: false,
  isLoading: false,
  error: null,
  abortController: null,

  setSessions: (sessions) => set({ sessions }),
  setCurrentSession: (currentSession) => set({ currentSession }),
  addSession: (session) => set((state) => ({
    sessions: [session, ...state.sessions],
  })),
  updateSession: (session) => set((state) => ({
    sessions: state.sessions.map((s) => (s.id === session.id ? session : s)),
    currentSession: state.currentSession?.id === session.id ? session : state.currentSession,
  })),
  removeSession: (id) => set((state) => ({
    sessions: state.sessions.filter((s) => s.id !== id),
    currentSession: state.currentSession?.id === id ? null : state.currentSession,
  })),
  setMessages: (messages: ChatMessage[] | ((prev: ChatMessage[]) => ChatMessage[])) => set((state) => ({
    messages: typeof messages === 'function' ? messages(state.messages) : messages,
  })),
  addMessage: (message: ChatMessage) => set((state) => ({
    messages: [...state.messages, message],
  })),
  updateMessage: (id: string, updates: Partial<ChatMessage>) => set((state) => ({
    messages: state.messages.map((m) => (m.id === id ? { ...m, ...updates } : m)),
  })),
  clearMessages: () => set({ messages: [] }),
  setStreaming: (isStreaming) => set({ isStreaming }),
  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error }),
  setAbortController: (abortController) => set({ abortController }),
  abortStream: () => {
    const { abortController } = get()
    if (abortController) {
      abortController.abort()
      set({ abortController: null, isStreaming: false })
    }
  },
}))