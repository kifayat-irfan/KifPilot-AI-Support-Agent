import apiClient from './api'
import type {
  AdminStats,
  SystemHealth,
  TimeSeriesData,
  AdminOrganization,
  AdminUser,
  AdminActivity,
  AdminNotification,
  PaginatedResponse,
  QuickAction,
} from '@/types'

export interface AdminUserFilters {
  search?: string
  organization_id?: string
  role?: string
  is_active?: boolean
  page?: number
  page_size?: number
  sort_by?: string
  sort_order?: 'asc' | 'desc'
}

export interface AdminOrganizationFilters {
  search?: string
  is_active?: boolean
  page?: number
  page_size?: number
  sort_by?: string
  sort_order?: 'asc' | 'desc'
}

export interface AdminActivityFilters {
  type?: string
  organization_id?: string
  user_id?: string
  start_date?: string
  end_date?: string
  page?: number
  page_size?: number
}

export const adminApi = {
  // Statistics
  async getStats(): Promise<AdminStats> {
    const response = await apiClient.get<AdminStats>('/admin/stats')
    return response.data
  },

  // System Health
  async getSystemHealth(): Promise<SystemHealth> {
    const response = await apiClient.get<SystemHealth>('/admin/health')
    return response.data
  },

  // Time Series Data for Charts
  async getTimeSeriesData(days: number = 30): Promise<TimeSeriesData> {
    const response = await apiClient.get<TimeSeriesData>(`/admin/analytics/timeseries`, {
      params: { days }
    })
    return response.data
  },

  // Organizations
  async getOrganizations(filters?: AdminOrganizationFilters): Promise<PaginatedResponse<AdminOrganization>> {
    const params = new URLSearchParams()
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          params.append(key, String(value))
        }
      })
    }
    const response = await apiClient.get<PaginatedResponse<AdminOrganization>>('/admin/organizations', { params })
    return response.data
  },

  async getOrganization(id: string): Promise<AdminOrganization> {
    const response = await apiClient.get<AdminOrganization>(`/admin/organizations/${id}`)
    return response.data
  },

  async createOrganization(data: { name: string; slug: string; description?: string }): Promise<AdminOrganization> {
    const response = await apiClient.post<AdminOrganization>('/admin/organizations', data)
    return response.data
  },

  async updateOrganization(id: string, data: Partial<AdminOrganization>): Promise<AdminOrganization> {
    const response = await apiClient.patch<AdminOrganization>(`/admin/organizations/${id}`, data)
    return response.data
  },

  async deleteOrganization(id: string): Promise<void> {
    await apiClient.delete(`/admin/organizations/${id}`)
  },

  // Users
  async getUsers(filters?: AdminUserFilters): Promise<PaginatedResponse<AdminUser>> {
    const params = new URLSearchParams()
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          params.append(key, String(value))
        }
      })
    }
    const response = await apiClient.get<PaginatedResponse<AdminUser>>('/admin/users', { params })
    return response.data
  },

  async getUser(id: string): Promise<AdminUser> {
    const response = await apiClient.get<AdminUser>(`/admin/users/${id}`)
    return response.data
  },

  async updateUser(id: string, data: Partial<AdminUser>): Promise<AdminUser> {
    const response = await apiClient.patch<AdminUser>(`/admin/users/${id}`, data)
    return response.data
  },

  async deleteUser(id: string): Promise<void> {
    await apiClient.delete(`/admin/users/${id}`)
  },

  // Activity Log
  async getActivity(filters?: AdminActivityFilters): Promise<PaginatedResponse<AdminActivity>> {
    const params = new URLSearchParams()
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          params.append(key, String(value))
        }
      })
    }
    const response = await apiClient.get<PaginatedResponse<AdminActivity>>('/admin/activity', { params })
    return response.data
  },

  // Notifications
  async getNotifications(unreadOnly: boolean = false): Promise<AdminNotification[]> {
    const response = await apiClient.get<AdminNotification[]>('/admin/notifications', {
      params: { unread_only: unreadOnly }
    })
    return response.data
  },

  async markNotificationRead(id: string): Promise<void> {
    await apiClient.post(`/admin/notifications/${id}/read`)
  },

  async markAllNotificationsRead(): Promise<void> {
    await apiClient.post('/admin/notifications/read-all')
  },

  // Quick Actions
  async getQuickActions(): Promise<Array<{
    id: string
    label: string
    description: string
    icon: string
    href: string
    color: string
  }>> {
    const response = await apiClient.get('/admin/quick-actions')
    return response.data
  },
}

export default adminApi

// Re-export types for convenience
export type {
  AdminStats,
  SystemHealth,
  TimeSeriesData,
  AdminOrganization,
  AdminUser,
  AdminActivity,
  AdminNotification,
  QuickAction,
}