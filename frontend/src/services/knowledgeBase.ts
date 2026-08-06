import apiClient from './api'
import type {
  Document,
  KnowledgeBaseStats,
  PaginatedResponse,
} from '@/types'

export interface DocumentFilters {
  search?: string
  category?: string
  language?: string
  organization_id?: string
  status?: string
  created_after?: string
  created_before?: string
  page?: number
  page_size?: number
  sort_by?: string
  sort_order?: 'asc' | 'desc'
}

export interface BulkActionRequest {
  document_ids: string[]
  action: 'delete' | 'restore' | 'reindex'
}

export const knowledgeBaseService = {
  // Statistics
  async getStats(knowledgeBaseId: string): Promise<KnowledgeBaseStats> {
    const response = await apiClient.get<KnowledgeBaseStats>(`/knowledge-bases/${knowledgeBaseId}/stats`)
    return response.data
  },

  // Documents
  async getDocuments(
    knowledgeBaseId: string,
    filters?: DocumentFilters
  ): Promise<PaginatedResponse<Document>> {
    const params = new URLSearchParams()
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          params.append(key, String(value))
        }
      })
    }
    const response = await apiClient.get<PaginatedResponse<Document>>(
      `/documents/knowledge-base/${knowledgeBaseId}`,
      { params }
    )
    return response.data
  },

  async getDocument(knowledgeBaseId: string, documentId: string): Promise<Document> {
    const response = await apiClient.get<Document>(`/documents/${documentId}`)
    return response.data
  },

  async uploadDocument(
    knowledgeBaseId: string,
    file: File,
    onProgress?: (progress: number) => void
  ): Promise<Document> {
    const formData = new FormData()
    formData.append('file', file)
    
    const { accessToken } = await import('@/stores/authStore').then(m => m.useAuthStore.getState())
    
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest()
      xhr.open('POST', `${import.meta.env.VITE_API_URL}/documents/upload?knowledge_base_id=${knowledgeBaseId}`)
      
      if (accessToken) {
        xhr.setRequestHeader('Authorization', `Bearer ${accessToken}`)
      }
      
      xhr.upload.addEventListener('progress', (event) => {
        if (event.lengthComputable && onProgress) {
          onProgress(Math.round((event.loaded / event.total) * 100))
        }
      })
      
      xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            const data = JSON.parse(xhr.responseText)
            resolve(data)
          } catch {
            reject(new Error('Invalid response'))
          }
        } else {
          reject(new Error(`Upload failed: ${xhr.statusText}`))
        }
      })
      
      xhr.addEventListener('error', () => reject(new Error('Upload failed')))
      xhr.addEventListener('abort', () => reject(new Error('Upload aborted')))
      
      xhr.send(formData)
    })
  },

  async uploadMultipleDocuments(
    knowledgeBaseId: string,
    files: File[],
    onProgress?: (fileIndex: number, progress: number) => void
  ): Promise<Document[]> {
    const results: Document[] = []
    for (let i = 0; i < files.length; i++) {
      const result = await knowledgeBaseService.uploadDocument(
        knowledgeBaseId,
        files[i],
        (progress) => onProgress?.(i, progress)
      )
      results.push(result)
    }
    return results
  },

  async updateDocument(
    documentId: string,
    data: Partial<Document>
  ): Promise<Document> {
    const response = await apiClient.patch<Document>(`/documents/${documentId}`, data)
    return response.data
  },

  async deleteDocument(documentId: string): Promise<void> {
    await apiClient.delete(`/documents/${documentId}`)
  },

  async restoreDocument(documentId: string): Promise<Document> {
    const response = await apiClient.post<Document>(`/documents/${documentId}/restore`)
    return response.data
  },

  async reindexDocument(documentId: string): Promise<Document> {
    const response = await apiClient.post<Document>(`/documents/${documentId}/reindex`)
    return response.data
  },

  async bulkAction(
    knowledgeBaseId: string,
    request: BulkActionRequest
  ): Promise<{ success: number; failed: number }> {
    const response = await apiClient.post<{ success: number; failed: number }>(
      `/documents/bulk?knowledge_base_id=${knowledgeBaseId}`,
      request
    )
    return response.data
  },

  // Knowledge Bases
  async getKnowledgeBases(params?: { offset?: number; limit?: number }): Promise<PaginatedResponse<Document>> {
    const response = await apiClient.get<PaginatedResponse<Document>>('/knowledge-bases', { params })
    return response.data
  },

  async getKnowledgeBase(id: string): Promise<Document> {
    const response = await apiClient.get<Document>(`/knowledge-bases/${id}`)
    return response.data
  },

  async createKnowledgeBase(data: { name: string; description?: string; embedding_model?: string }): Promise<Document> {
    const response = await apiClient.post<Document>('/knowledge-bases', data)
    return response.data
  },

  async updateKnowledgeBase(id: string, data: Partial<Document>): Promise<Document> {
    const response = await apiClient.patch<Document>(`/knowledge-bases/${id}`, data)
    return response.data
  },

  async deleteKnowledgeBase(id: string): Promise<void> {
    await apiClient.delete(`/knowledge-bases/${id}`)
  },
}

export default knowledgeBaseService