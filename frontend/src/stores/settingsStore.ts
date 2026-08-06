import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'

type Theme = 'light' | 'dark' | 'system'

interface SettingsState {
  theme: Theme
  language: string
  sidebarCollapsed: boolean
  compactMode: boolean
  notificationsEnabled: boolean
  streamingEnabled: boolean
  citationsEnabled: boolean
  setTheme: (theme: Theme) => void
  setLanguage: (language: string) => void
  toggleSidebar: () => void
  setSidebarCollapsed: (collapsed: boolean) => void
  setCompactMode: (compact: boolean) => void
  setNotificationsEnabled: (enabled: boolean) => void
  setStreamingEnabled: (enabled: boolean) => void
  setCitationsEnabled: (enabled: boolean) => void
  reset: () => void
}

const defaultState = {
  theme: 'system' as const,
  language: 'en',
  sidebarCollapsed: false,
  compactMode: false,
  notificationsEnabled: true,
  streamingEnabled: true,
  citationsEnabled: true,
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      ...defaultState,
      setTheme: (theme: Theme) => set({ theme }),
      setLanguage: (language: string) => set({ language }),
      toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
      setSidebarCollapsed: (sidebarCollapsed: boolean) => set({ sidebarCollapsed }),
      setCompactMode: (compactMode: boolean) => set({ compactMode }),
      setNotificationsEnabled: (notificationsEnabled: boolean) => set({ notificationsEnabled }),
      setStreamingEnabled: (streamingEnabled: boolean) => set({ streamingEnabled }),
      setCitationsEnabled: (citationsEnabled: boolean) => set({ citationsEnabled }),
      reset: () => set(defaultState),
    }),
    {
      name: 'settings-storage',
      storage: createJSONStorage(() => localStorage),
    }
  )
)