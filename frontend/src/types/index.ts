// 用户相关
export interface User {
  id: string
  email: string
  display_name: string | null
  avatar_url: string | null
  role: 'admin' | 'auditor' | 'member'
  department_id: string | null
  department_name: string | null
  created_at: string
}

export interface LoginRequest {
  email: string
  password: string
}

export interface RegisterRequest {
  email: string
  password: string
  display_name?: string
}

export interface AuthResponse {
  code: number
  message: string
  data: {
    user: User
    access_token: string
    token_type: string
  }
}

// 对话相关
export interface Conversation {
  id: string
  title: string
  knowledge_base_id?: string | null
  message_count?: number
  created_at: string
  updated_at: string
}

export interface ToolCall {
  id: string
  name: string
  arguments: Record<string, unknown>
  result?: unknown
  status: 'running' | 'success' | 'error'
  started_at?: string
  completed_at?: string
  duration_ms?: number
}

export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  token_count: number | null
  latency_ms: number | null
  created_at: string
  tool_calls?: ToolCall[]
  feedback?: 'up' | 'down' | null
}

export interface ConversationDetail extends Conversation {
  knowledge_base_id: string | null
  messages: Message[]
}

export interface PaginatedConversations {
  items: Array<Conversation & { message_count?: number }>
  total: number
}

// 知识库相关
export interface KnowledgeBase {
  id: string
  name: string
  description: string | null
  document_count: number
  is_active: boolean
  is_shared?: boolean
  shared_by?: string | null
  created_at: string
  updated_at: string
}

export interface KnowledgeDocument {
  id: string
  filename: string
  file_size: number | null
  file_type: string | null
  upload_status: string
  error_message: string | null
  created_at: string
}

// API 通用响应
export interface ApiResponse<T = unknown> {
  code: number
  message: string
  data: T
}

// 知识库分享相关
export interface ShareCode {
  id: string
  share_code: string
  permission: string
  is_active: boolean
  is_expired: boolean
  expires_at: string | null
  created_at: string | null
}

export interface SharedKnowledgeBase {
  id: string
  name: string
  description: string | null
  permission: string
  shared_by: string
  accessed_at: string
}

export interface AccessLog {
  id: string
  user_id: string
  email: string
  display_name: string | null
  action: string
  detail: string | null
  share_code: string | null
  ip_address: string | null
  created_at: string | null
}

// 搜索相关
export interface SearchResultMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
  highlight: string
}

export interface SearchResultItem {
  conversation_id: string
  conversation_title: string
  messages: SearchResultMessage[]
}

export interface SearchResult {
  total: number
  items: SearchResultItem[]
}
