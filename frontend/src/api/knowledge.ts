import request from './request'
import type { ApiResponse, KnowledgeBase, KnowledgeDocument } from '../types'

export interface PaginatedKnowledgeBases {
  items: KnowledgeBase[]
  total: number
  page: number
  page_size: number
}

export interface PaginatedDocuments {
  items: KnowledgeDocument[]
  total: number
  page: number
  page_size: number
}

export function listKnowledgeBases(page = 1, page_size = 20) {
  return request.get<ApiResponse<PaginatedKnowledgeBases>>('/knowledge/bases', {
    params: { page, page_size },
  })
}

export function getKnowledgeBase(id: string) {
  return request.get<ApiResponse<KnowledgeBase>>(`/knowledge/bases/${id}`)
}

export function createKnowledgeBase(data: { name: string; description?: string; chat_provider?: string; chat_model?: string }) {
  return request.post<ApiResponse<KnowledgeBase>>('/knowledge/bases', data)
}

export function renameKnowledgeBase(id: string, data: { name: string; description?: string }) {
  return request.put<ApiResponse<KnowledgeBase>>(`/knowledge/bases/${id}`, data)
}

export function deleteKnowledgeBase(id: string) {
  return request.delete<ApiResponse<null>>(`/knowledge/bases/${id}`)
}

export function listDocuments(baseId: string, page = 1, page_size = 20) {
  return request.get<ApiResponse<PaginatedDocuments>>(`/knowledge/bases/${baseId}/documents`, {
    params: { page, page_size },
  })
}

export function uploadDocument(baseId: string, file: File) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post<ApiResponse<KnowledgeDocument>>(`/knowledge/bases/${baseId}/documents`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function deleteDocument(docId: string) {
  return request.delete<ApiResponse<null>>(`/knowledge/documents/${docId}`)
}

export function previewDocument(docId: string) {
  return request.get<ApiResponse<{ type: string; content?: string; file_url?: string }>>(`/knowledge/documents/${docId}/preview`)
}

// 知识库成员管理
export interface KnowledgeBaseMember {
  id: string
  user_id: string
  email: string
  display_name: string | null
  permission: string
  created_at: string
}

export function listKnowledgeBaseMembers(kbId: string) {
  return request.get<ApiResponse<KnowledgeBaseMember[]>>(`/knowledge/bases/${kbId}/members`)
}

export function addKnowledgeBaseMember(kbId: string, data: { user_id?: string; email?: string; permission?: string }) {
  return request.post<ApiResponse<KnowledgeBaseMember>>(`/knowledge/bases/${kbId}/members`, data)
}

export function removeKnowledgeBaseMember(kbId: string, userId: string) {
  return request.delete<ApiResponse<null>>(`/knowledge/bases/${kbId}/members/${userId}`)
}

export function updateKnowledgeBaseMemberPermission(kbId: string, userId: string, data: { permission: string }) {
  return request.put<ApiResponse<KnowledgeBaseMember>>(`/knowledge/bases/${kbId}/members/${userId}`, data)
}

// 用户列表（供知识库成员管理使用，无需 admin 权限）
export interface UserItem {
  id: string
  email: string
  display_name: string | null
  role: string
  is_active: boolean
}

export function listAllUsers() {
  return request.get<ApiResponse<{ items: UserItem[]; total: number }>>('/knowledge/users')
}
