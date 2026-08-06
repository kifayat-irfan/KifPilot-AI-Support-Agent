import apiClient from './api'
import type {
  Document,
  PaginatedResponse,
  SearchRequest,
  SearchResponse,
  RetrievalResult,
  RAGRequest,
  RAGResponse,
  Citation,
} from '@/types'

export const documentsApi = {
  list: async (params?: {
    category?: string
    language?: string
    status?: string
    search?: string
    sort_by?: string
    sort_order?: string
    page?: number
    page_size?: number
  }): Promise<PaginatedResponse<Document>> => {
    const response = await apiClient.get<PaginatedResponse<Document>>('/documents', { params })
    return response.data
  },

  get: async (id: string): Promise<Document> => {
    const response = await apiClient.get<Document>(`/documents/${id}`)
    return response.data
  },

  upload: async (file: File, metadata?: {
    title?: string
    description?: string
    category?: string
    tags?: string[]
    language?: string
    force_reindex?: boolean
  }): Promise<Document> => {
    const formData = new FormData()
    formData.append('file', file)
    if (metadata?.title) formData.append('title', metadata.title)
    if (metadata?.description) formData.append('description', metadata.description)
    if (metadata?.category) formData.append('category', metadata.category)
    if (metadata?.tags) formData.append('tags', metadata.tags.join(','))
    if (metadata?.language) formData.append('language', metadata.language)
    if (metadata?.force_reindex) formData.append('force_reindex', 'true')

    const response = await apiClient.post<Document>('/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return response.data
  },

  update: async (id: string, data: Partial<Document>): Promise<Document> => {
    const response = await apiClient.patch<Document>(`/documents/${id}`, data)
    return response.data
  },

  delete: async (id: string, hard?: boolean): Promise<void> => {
    await apiClient.delete(`/documents/${id}`, { params: { hard } })
  },

  restore: async (id: string): Promise<Document> => {
    const response = await apiClient.post<Document>(`/documents/${id}/restore`)
    return response.data
  },

  getChunks: async (id: string): Promise<Array<{
    chunk_id: string
    chunk_index: number
    text: string
    page: number | null
    section: string | null
    heading: string | null
    token_count: number
  }>> => {
    const response = await apiClient.get(`/documents/${id}/chunks`)
    return response.data
  },
}

export const retrievalApi = {
  search: async (data: SearchRequest): Promise<SearchResponse> => {
    const response = await apiClient.post<SearchResponse>('/retrieval/search', data)
    return response.data
  },

  buildContext: async (data: {
    query: string
    top_k: number
    minimum_score: number
    max_context_chars: number
    filters?: Record<string, unknown>
  }): Promise<{ context: string; sources: RetrievalResult[]; search_time_ms: number }> => {
    const response = await apiClient.post('/retrieval/context', data)
    return response.data
  },

  healthCheck: async (): Promise<{ status: string; vector_store_connected: boolean; embedding_service_available: boolean }> => {
    const response = await apiClient.get('/retrieval/health')
    return response.data
  },
}

export const ragApi = {
  ask: async (data: RAGRequest): Promise<RAGResponse> => {
    const response = await apiClient.post<RAGResponse>('/rag/ask', data)
    return response.data
  },

  healthCheck: async (): Promise<{ status: string; retrieval_service_healthy: boolean; ollama_service_healthy: boolean }> => {
    const response = await apiClient.get('/rag/health')
    return response.data
  },
}

export const citationsApi = {
  askWithCitations: async (data: {
    question: string
    top_k: number
    minimum_score: number
    filters?: Record<string, unknown>
  }): Promise<{ answer: string; citations: Citation[]; confidence: number; sources_found: number; response_time_ms: number }> => {
    const response = await apiClient.post('/citations/ask', data)
    return response.data
  },

  healthCheck: async (): Promise<{ status: string; citation_service_healthy: boolean; retrieval_service_healthy: boolean }> => {
    const response = await apiClient.get('/citations/health')
    return response.data
  },
}

export const chatApi = {
  stream: async (data: {
    question: string
    session_id?: string
    top_k: number
    minimum_score: number
    filters?: Record<string, unknown>
    memory_config?: {
      max_messages: number
      max_tokens: number
      include_system_prompt: boolean
    }
  }, onEvent: (event: { type: string; data: unknown }) => void): Promise<void> => {
    const response = await fetch(`${apiClient.defaults.baseURL}/chat/session/${data.session_id || ''}/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}`,
      },
      body: JSON.stringify(data),
    })

    if (!response.ok) {
      throw new Error('Stream request failed')
    }

    const reader = response.body?.getReader()
    const decoder = new TextDecoder()

    if (!reader) return

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      const chunk = decoder.decode(value)
      const lines = chunk.split('\n\n')

      for (const line of lines) {
        if (line.startsWith('event: ')) {
          const eventType = line.slice(7).trim()
          const dataLine = lines[lines.indexOf(line) + 1]
          if (dataLine?.startsWith('data: ')) {
            try {
              const eventData = JSON.parse(dataLine.slice(6))
              onEvent({ type: eventType, data: eventData })
            } catch {
              // Ignore parse errors
            }
          }
        }
      }
    }
  },

  ask: async (data: {
    question: string
    session_id?: string
    top_k: number
    minimum_score: number
    filters?: Record<string, unknown>
    memory_config?: {
      max_messages: number
      max_tokens: number
      include_system_prompt: boolean
    }
  }): Promise<{ answer: string; citations: Citation[]; confidence: number; sources_found: number; response_time_ms: number; session_id: string }> => {
    const response = await apiClient.post('/chat/session/ask', data)
    return response.data
  },

  listSessions: async (params?: {
    page?: number
    page_size?: number
    sort_by?: string
    sort_order?: string
  }): Promise<PaginatedResponse<{
    id: string
    title: string | null
    created_at: string
    updated_at: string
    last_activity: string
    message_count: number
  }>> => {
    const response = await apiClient.get('/chat/session', { params })
    return response.data
  },

  getSession: async (sessionId: string): Promise<{
    session: {
      id: string
      title: string | null
      created_at: string
      updated_at: string
      last_activity: string
      message_count: number
    }
    messages: Array<{
      id: string
      session_id: string
      role: string
      message: string
      citations: Citation[] | null
      confidence: number | null
      token_count: number | null
      response_time_ms: number | null
      created_at: string
    }>
  }> => {
    const response = await apiClient.get(`/chat/session/${sessionId}`)
    return response.data
  },

  createSession: async (title?: string): Promise<{
    id: string
    title: string | null
    created_at: string
    updated_at: string
    last_activity: string
    message_count: number
  }> => {
    const response = await apiClient.post('/chat/session', { title })
    return response.data
  },

  updateSession: async (sessionId: string, title: string): Promise<{
    id: string
    title: string | null
    created_at: string
    updated_at: string
    last_activity: string
    message_count: number
  }> => {
    const response = await apiClient.patch(`/chat/session/${sessionId}`, { title })
    return response.data
  },

  deleteSession: async (sessionId: string): Promise<void> => {
    await apiClient.delete(`/chat/session/${sessionId}`)
  },
}

export const usersApi = {
  list: async (params?: { skip?: number; limit?: number }): Promise<PaginatedResponse<{
    id: string
    email: string
    username: string
    is_active: boolean
    created_at: string
    updated_at: string
    roles: Array<{ id: string; name: string }>
  }>> => {
    const response = await apiClient.get('/auth/users', { params })
    return response.data
  },

  get: async (id: string): Promise<{
    id: string
    email: string
    username: string
    is_active: boolean
    created_at: string
    updated_at: string
    roles: Array<{ id: string; name: string }>
  }> => {
    const response = await apiClient.get(`/auth/users/${id}`)
    return response.data
  },

  update: async (id: string, data: { email?: string; username?: string; is_active?: boolean }): Promise<{
    id: string
    email: string
    username: string
    is_active: boolean
    created_at: string
    updated_at: string
    roles: Array<{ id: string; name: string }>
  }> => {
    const response = await apiClient.patch(`/auth/users/${id}`, data)
    return response.data
  },

  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/auth/users/${id}`)
  },

  listRoles: async (): Promise<Array<{
    id: string
    name: string
    description: string | null
    permissions: Array<{ id: string; name: string }>
  }>> => {
    const response = await apiClient.get('/auth/roles')
    return response.data
  },

  listPermissions: async (): Promise<Array<{
    id: string
    name: string
    description: string | null
  }>> => {
    const response = await apiClient.get('/auth/permissions')
    return response.data
  },
}