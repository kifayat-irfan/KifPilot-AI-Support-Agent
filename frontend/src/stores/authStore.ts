import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import type { User, TokenResponse, Organization } from '@/types'

interface AuthState {
  user: User | null
  accessToken: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  isLoading: boolean
  currentOrganization: Organization | null
  setTokens: (accessToken: string, refreshToken: string) => void
  setUser: (user: User) => void
  setCurrentOrganization: (org: Organization | null) => void
  logout: () => void
  setLoading: (loading: boolean) => void
  hasPermission: (permission: string) => boolean
  hasRole: (role: string) => boolean
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: true,
      currentOrganization: null,

      setTokens: (accessToken, refreshToken) => {
        set({ accessToken, refreshToken, isAuthenticated: true })
        localStorage.setItem('access_token', accessToken)
        localStorage.setItem('refresh_token', refreshToken)
      },

      setUser: (user) => {
        set({ user, isAuthenticated: true })
      },

      setCurrentOrganization: (organization) => {
        set({ currentOrganization: organization })
        if (organization) {
          localStorage.setItem('current_organization_id', organization.id)
        } else {
          localStorage.removeItem('current_organization_id')
        }
      },

      logout: () => {
        set({
          user: null,
          accessToken: null,
          refreshToken: null,
          isAuthenticated: false,
          currentOrganization: null,
        })
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        localStorage.removeItem('current_organization_id')
      },

      setLoading: (isLoading) => {
        set({ isLoading })
      },

      hasPermission: (permission) => {
        const { user } = get()
        if (!user) return false
        return user.roles.some((role) =>
          role.permissions.some((p) => p.name === permission)
        )
      },

      hasRole: (roleName) => {
        const { user } = get()
        if (!user) return false
        return user.roles.some((role) => role.name === roleName)
      },
    }),
    {
      name: 'auth-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        user: state.user,
        currentOrganization: state.currentOrganization,
      }),
      onRehydrateStorage: () => (state) => {
        if (state) {
          state.setLoading(false)
        }
      },
    }
  )
)