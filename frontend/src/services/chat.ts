import apiClient, { uploadFile } from './api'

export interface ChatRequest {
  message: string
  conversation_id?: string
  session_id?: string
  knowledge_base_ids?: string[]
  temperature?: number
  max_tokens?: number
  stream?: boolean
  memory_config?: {
    max_messages: number
    max_tokens: number
    include_system_prompt: boolean
  }
}

export interface ChatResponse {
  conversation_id: string
  message: Message
  sources: Source[]
}

export interface Message {
  id: string
  conversation_id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  tokens_used: number
  model_used?: string
  metadata: Record<string, any>
  created_at: string
}

export interface Source {
  id: string
  document_id: string
  knowledge_base_id: string
  content: string
  chunk_index: number
  token_count: number
  metadata: Record<string, any>
  created_at: string
  score: number
}

export interface Conversation {
  id: string
  user_id?: string
  session_id: string
  status: 'active' | 'closed' | 'escalated'
  title?: string
  metadata: Record<string, any>
  created_at: string
  updated_at: string
  message_count: number
}

export interface KnowledgeBase {
  id: string
  name: string
  description?: string
  status: 'active' | 'inactive' | 'processing'
  document_count: number
  chunk_count: number
  embedding_model: string
  metadata: Record<string, any>
  created_at: string
  updated_at: string
}

export interface Document {
  id: string
  knowledge_base_id: string
  filename: string
  content_type: string
  size_bytes: number
  status: string
  chunk_count: number
  metadata: Record<string, any>
  created_at: string
  updated_at: string
}

export interface SearchRequest {
  query: string
  knowledge_base_ids?: string[]
  limit?: number
  threshold?: number
}

export interface SearchResult {
  chunk: Source
  score: number
}

export interface SearchResponse {
  results: SearchResult[]
  query: string
}

export type StreamEventType = 
  | 'start'
  | 'retrieval'
  | 'token'
  | 'citations'
  | 'complete'
  | 'error'

export interface StreamEvent {
  type: StreamEventType
  data: {
    text?: string
    chunks_found?: number
    search_time_ms?: number
    citations?: Citation[]
    confidence?: number
    sources_found?: number
    response_time_ms?: number
    error?: string
    code?: string
  }
}

export interface Citation {
  document_id: string
  document_name: string
  page_number: number | null
  section: string | null
  chunk_id: string
  chunk_index: number
  similarity_score: number
}

async function* parseSSEStream(stream: ReadableStream): AsyncGenerator<StreamEvent> {
  const reader = stream.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (!line.trim()) continue
        
        const eventMatch = line.match(/^event:\s*(.+)$/m)
        const dataMatch = line.match(/^data:\s*(.+)$/m)
        
        if (eventMatch && dataMatch) {
          const type = eventMatch[1].trim() as StreamEventType
          try {
            const data = JSON.parse(dataMatch[1].trim())
            yield { type, data }
          } catch {
            // Skip invalid JSON
          }
        }
      }
    }
  } finally {
    reader.releaseLock()
  }
}

export const chatService = {
  async sendMessage(request: ChatRequest): Promise<{ message: Message; sources: Source[] }> {
    const response = await apiClient.post('/chat', request)
    return response.data
  },

  async *sendMessageStream(request: ChatRequest): AsyncGenerator<StreamEvent> {
    const response = await fetch(`${import.meta.env.VITE_API_URL}/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${localStorage.getItem('kifpilot_auth_token')}`,
      },
      body: JSON.stringify(request),
    })
    if (!response.body) throw new Error('No response body')
    
    for await (const event of parseSSEStream(response.body)) {
      yield event
    }
  },

  async getConversations(params?: { offset?: number; limit?: number }): Promise<Conversation[]> {
    const response = await apiClient.get('/conversations', { params })
    return response.data
  },

  async getConversation(id: string): Promise<Conversation> {
    const response = await apiClient.get(`/conversations/${id}`)
    return response.data
  },

  async createConversation(data: { session_id: string; user_id?: string; title?: string }): Promise<Conversation> {
    const response = await apiClient.post('/conversations', data)
    return response.data
  },

  async updateConversation(id: string, data: Partial<Conversation>): Promise<Conversation> {
    const response = await apiClient.patch(`/conversations/${id}`, data)
    return response.data
  },

  async deleteConversation(id: string): Promise<void> {
    await apiClient.delete(`/conversations/${id}`)
  },

  async getMessages(conversationId: string, params?: { offset?: number; limit?: number }): Promise<Message[]> {
    const response = await apiClient.get(`/messages/conversation/${conversationId}`, { params })
    return response.data
  },

  async getKnowledgeBases(params?: { offset?: number; limit?: number }): Promise<KnowledgeBase[]> {
    const response = await apiClient.get('/knowledge-bases', { params })
    return response.data
  },

  async getKnowledgeBase(id: string): Promise<KnowledgeBase> {
    const response = await apiClient.get(`/knowledge-bases/${id}`)
    return response.data
  },

  async createKnowledgeBase(data: { name: string; description?: string; embedding_model?: string }): Promise<KnowledgeBase> {
    const response = await apiClient.post('/knowledge-bases', data)
    return response.data
  },

  async updateKnowledgeBase(id: string, data: Partial<KnowledgeBase>): Promise<KnowledgeBase> {
    const response = await apiClient.patch(`/knowledge-bases/${id}`, data)
    return response.data
  },

  async deleteKnowledgeBase(id: string): Promise<void> {
    await apiClient.delete(`/knowledge-bases/${id}`)
  },

  async uploadDocument(knowledgeBaseId: string, file: File): Promise<Document> {
    const formData = new FormData()
    formData.append('file', file)
    return uploadFile(`/documents/upload?knowledge_base_id=${knowledgeBaseId}`, formData)
  },

  async getDocuments(knowledgeBaseId: string, params?: { offset?: number; limit?: number }): Promise<Document[]> {
    const response = await apiClient.get(`/documents/knowledge-base/${knowledgeBaseId}`, { params })
    return response.data
  },

  async processDocument(documentId: string): Promise<void> {
    await apiClient.post(`/documents/${documentId}/process`)
  },

  async deleteDocument(documentId: string): Promise<void> {
    await apiClient.delete(`/documents/${documentId}`)
  },

  async search(request: SearchRequest): Promise<SearchResponse> {
    const response = await apiClient.post('/search', request)
    return response.data
  },

  async healthCheck(): Promise<any> {
    const response = await apiClient.get('/health')
    return response.data
  },
}