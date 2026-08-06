import apiClient from './api'
import type {
  LoginRequest,
  RegisterRequest,
  TokenResponse,
  RefreshTokenRequest,
  User,
  Organization,
  OrganizationMember,
  OrganizationSettings,
  PaginatedResponse,
} from '@/types'

export const authApi = {
  login: async (data: LoginRequest): Promise<TokenResponse> => {
    const response = await apiClient.post<TokenResponse>('/auth/login', data)
    return response.data
  },

  register: async (data: RegisterRequest): Promise<User> => {
    const response = await apiClient.post<User>('/auth/register', data)
    return response.data
  },

  refreshToken: async (data: RefreshTokenRequest): Promise<TokenResponse> => {
    const response = await apiClient.post<TokenResponse>('/auth/refresh', data)
    return response.data
  },

  getMe: async (): Promise<User> => {
    const response = await apiClient.get<User>('/auth/me')
    return response.data
  },

  logout: async (): Promise<void> => {
    await apiClient.post('/auth/logout')
  },

  updateProfile: async (data: Partial<User>): Promise<User> => {
    const response = await apiClient.patch<User>('/auth/me', data)
    return response.data
  },

  changePassword: async (currentPassword: string, newPassword: string): Promise<void> => {
    await apiClient.post('/auth/me/password', { current_password: currentPassword, new_password: newPassword })
  },
}

export const organizationsApi = {
  list: async (params?: { page?: number; page_size?: number; is_active?: boolean }): Promise<PaginatedResponse<Organization>> => {
    const response = await apiClient.get<PaginatedResponse<Organization>>('/organizations', { params })
    return response.data
  },

  get: async (id: string): Promise<Organization> => {
    const response = await apiClient.get<Organization>(`/organizations/${id}`)
    return response.data
  },

  create: async (data: { name: string; slug: string; description?: string }): Promise<Organization> => {
    const response = await apiClient.post<Organization>('/organizations', data)
    return response.data
  },

  update: async (id: string, data: Partial<Organization>): Promise<Organization> => {
    const response = await apiClient.patch<Organization>(`/organizations/${id}`, data)
    return response.data
  },

  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/organizations/${id}`)
  },

  listMembers: async (organizationId: string): Promise<OrganizationMember[]> => {
    const response = await apiClient.get<OrganizationMember[]>(`/organizations/${organizationId}/members`)
    return response.data
  },

  addMember: async (organizationId: string, data: { user_id: string; role: 'owner' | 'admin' | 'member' }): Promise<OrganizationMember> => {
    const response = await apiClient.post<OrganizationMember>(`/organizations/${organizationId}/members`, data)
    return response.data
  },

  removeMember: async (organizationId: string, userId: string): Promise<void> => {
    await apiClient.delete(`/organizations/${organizationId}/members/${userId}`)
  },

  updateMemberRole: async (organizationId: string, userId: string, role: 'owner' | 'admin' | 'member'): Promise<OrganizationMember> => {
    const response = await apiClient.patch<OrganizationMember>(`/organizations/${organizationId}/members/${userId}/role`, { role })
    return response.data
  },

  getSettings: async (organizationId: string): Promise<OrganizationSettings> => {
    const response = await apiClient.get<OrganizationSettings>(`/organizations/${organizationId}/settings`)
    return response.data
  },

  updateSettings: async (organizationId: string, data: Partial<OrganizationSettings>): Promise<OrganizationSettings> => {
    const response = await apiClient.patch<OrganizationSettings>(`/organizations/${organizationId}/settings`, data)
    return response.data
  },
}