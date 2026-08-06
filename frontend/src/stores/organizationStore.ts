import { create } from 'zustand'
import type { Organization, OrganizationMember, OrganizationSettings } from '@/types'

interface OrganizationState {
  organizations: Organization[]
  currentOrganization: Organization | null
  members: OrganizationMember[]
  settings: OrganizationSettings | null
  isLoading: boolean
  error: string | null
  setOrganizations: (orgs: Organization[]) => void
  setCurrentOrganization: (org: Organization | null) => void
  addOrganization: (org: Organization) => void
  updateOrganization: (org: Organization) => void
  removeOrganization: (id: string) => void
  setMembers: (members: OrganizationMember[]) => void
  addMember: (member: OrganizationMember) => void
  removeMember: (userId: string) => void
  updateMemberRole: (userId: string, role: OrganizationMember['role']) => void
  setSettings: (settings: OrganizationSettings) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  clearError: () => void
}

export const useOrganizationStore = create<OrganizationState>((set) => ({
  organizations: [],
  currentOrganization: null,
  members: [],
  settings: null,
  isLoading: false,
  error: null,

  setOrganizations: (organizations) => set({ organizations }),
  setCurrentOrganization: (currentOrganization) => set({ currentOrganization }),
  addOrganization: (organization) => set((state) => ({
    organizations: [organization, ...state.organizations],
  })),
  updateOrganization: (organization) => set((state) => ({
    organizations: state.organizations.map((o) => (o.id === organization.id ? organization : o)),
    currentOrganization: state.currentOrganization?.id === organization.id ? organization : state.currentOrganization,
  })),
  removeOrganization: (id) => set((state) => ({
    organizations: state.organizations.filter((o) => o.id !== id),
    currentOrganization: state.currentOrganization?.id === id ? null : state.currentOrganization,
  })),
  setMembers: (members) => set({ members }),
  addMember: (member) => set((state) => ({
    members: [...state.members, member],
  })),
  removeMember: (userId) => set((state) => ({
    members: state.members.filter((m) => m.user_id !== userId),
  })),
  updateMemberRole: (userId, role) => set((state) => ({
    members: state.members.map((m) => (m.user_id === userId ? { ...m, role } : m)),
  })),
  setSettings: (settings) => set({ settings }),
  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error }),
  clearError: () => set({ error: null }),
}))