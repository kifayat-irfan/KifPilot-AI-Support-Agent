export interface User {
  id: string
  email: string
  username: string
  is_active: boolean
  created_at: string
  updated_at: string
  roles: Role[]
}

export interface Role {
  id: string
  name: 'admin' | 'manager' | 'editor' | 'viewer'
  description: string | null
  permissions: Permission[]
}

export interface Permission {
  id: string
  name: string
  description: string | null
}

export interface Organization {
  id: string
  name: string
  slug: string
  description: string | null
  is_active: boolean
  created_at: string
  updated_at: string
  member_count: number
  members?: OrganizationMember[]
  settings?: OrganizationSettings
}

export interface OrganizationMember {
  user_id: string
  username: string
  email: string
  role: 'owner' | 'admin' | 'member'
  joined_at: string
}

export interface OrganizationSettings {
  id: string
  organization_id: string
  default_top_k: number
  default_min_score: number
  default_max_context: number
  max_message_history: number
  max_tokens_context: number
  embedding_model: string
  enable_streaming: boolean
  enable_citations: boolean
  enable_conversation_memory: boolean
  created_at: string
  updated_at: string
}

export interface Document {
  id: string
  filename: string
  original_filename: string
  title: string | null
  description: string | null
  category: string | null
  tags: string[] | null
  language: string | null
  file_type: string
  mime_type: string
  file_size: number
  status: 'uploading' | 'parsing' | 'chunking' | 'embedding' | 'storing' | 'completed' | 'failed'
  page_count: number
  chunk_count: number
  embeddings_created: number
  error_message: string | null
  processing_time_ms: number | null
  created_at: string
  updated_at: string
  deleted_at: string | null
  knowledge_base_id?: string
  organization_id?: string
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

export interface KnowledgeBaseStats {
  total_documents: number
  indexed_documents: number
  processing_documents: number
  failed_documents: number
  storage_used_bytes: number
}

export interface ChatSession {
  id: string
  organization_id: string
  title: string | null
  message_count: number
  last_activity: string
  created_at: string
  updated_at: string
  messages?: ChatMessage[]
}

export interface ChatMessage {
  id: string
  session_id: string
  role: 'user' | 'assistant' | 'system'
  message: string
  content?: string
  timestamp?: string
  citations: Citation[] | null
  confidence: number | null
  token_count: number | null
  response_time_ms: number | null
  created_at: string
  feedback?: 'positive' | 'negative'
  isStreaming?: boolean
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

export interface RetrievalResult {
  document_id: string
  document_name: string
  chunk_id: string
  chunk_index: number
  page: number | null
  section: string | null
  text: string
  similarity_score: number
  metadata: Record<string, unknown>
}

export interface SearchRequest {
  query: string
  top_k: number
  minimum_score: number
  filters?: Record<string, unknown>
}

export interface SearchResponse {
  results: RetrievalResult[]
  total_results: number
  search_time_ms: number
}

export interface RAGRequest {
  question: string
  top_k: number
  minimum_score: number
  filters?: Record<string, unknown>
}

export interface RAGResponse {
  answer: string
  citations: Citation[]
  confidence: number
  sources_found: number
  response_time_ms: number
}

export interface StreamEvent {
  type: 'start' | 'retrieval' | 'token' | 'citations' | 'complete' | 'error'
  data: unknown
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface ApiError {
  error: string
  code: string
  details?: Record<string, unknown>
}

export interface LoginRequest {
  username: string
  password: string
}

export interface RegisterRequest {
  email: string
  username: string
  password: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface RefreshTokenRequest {
  refresh_token: string
}

export interface AdminStats {
  total_organizations: number
  total_users: number
  total_documents: number
  indexed_documents: number
  chat_sessions: number
  total_messages: number
  storage_used_bytes: number
  avg_response_time_ms: number
}

export interface SystemHealth {
  backend: 'healthy' | 'degraded' | 'down'
  database: 'healthy' | 'degraded' | 'down'
  ollama: 'healthy' | 'degraded' | 'down'
  chromadb: 'healthy' | 'degraded' | 'down'
  vector_collections: 'healthy' | 'degraded' | 'down'
  api: 'healthy' | 'degraded' | 'down'
  background_services: 'healthy' | 'degraded' | 'down'
}

export interface ChartDataPoint {
  date: string
  value: number
}

export interface TimeSeriesData {
  documents_uploaded: ChartDataPoint[]
  questions_per_day: ChartDataPoint[]
  response_time_trend: ChartDataPoint[]
  active_users: ChartDataPoint[]
  storage_growth: ChartDataPoint[]
}

export interface AdminOrganization {
  id: string
  name: string
  slug: string
  description: string | null
  is_active: boolean
  member_count: number
  document_count: number
  storage_used_bytes: number
  created_at: string
}

export interface AdminUser {
  id: string
  email: string
  username: string
  is_active: boolean
  created_at: string
  updated_at: string
  roles: Role[]
  organization_name: string
  last_login: string | null
}

export interface AdminActivity {
  id: string
  type: 'document_upload' | 'login' | 'chat_session' | 'error' | 'reindex_job' | 'organization_created' | 'user_created'
  title: string
  description: string
  organization_id: string
  organization_name: string
  user_id: string | null
  username: string | null
  metadata: Record<string, unknown>
  created_at: string
}

export interface AdminNotification {
  id: string
  type: 'failed_indexing' | 'system_error' | 'model_offline' | 'database_issue' | 'storage_warning'
  severity: 'info' | 'warning' | 'critical'
  title: string
  message: string
  organization_id: string | null
  is_read: boolean
  created_at: string
}

export interface QuickAction {
  id: string
  label: string
  description: string
  icon: string
  href: string
  color: string
}