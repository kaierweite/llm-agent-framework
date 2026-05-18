import request from './request'
import type { ApiResponse } from '../types'

export interface AdminUser {
  id: string
  email: string
  display_name: string | null
  role: string
  is_active: boolean
  department_id: string | null
  department_name: string | null
  created_at: string
  updated_at: string
}

export interface SystemStats {
  total_users: number
  active_users: number
  total_conversations: number
  total_knowledge_bases: number
  total_documents: number
}

export interface AdminSkill {
  id: string
  name: string
  display_name: string
  description: string | null
  version: string
  author: string | null
  is_enabled: boolean
  config_schema: string | null
  created_at: string
  updated_at: string
}

export interface PaginatedUsers {
  items: AdminUser[]
  total: number
  page: number
  page_size: number
}

export interface PaginatedSkills {
  items: AdminSkill[]
  total: number
  page: number
  page_size: number
}

export function getUsers(page = 1, page_size = 20) {
  return request.get<ApiResponse<PaginatedUsers>>('/admin/users', {
    params: { page, page_size },
  })
}

export function listUsers() {
  return request.get<ApiResponse<PaginatedUsers>>('/admin/users', {
    params: { page: 1, page_size: 1000 },
  })
}

export function getUser(userId: string) {
  return request.get<ApiResponse<AdminUser>>(`/admin/users/${userId}`)
}

export function updateUserRole(userId: string, role: string) {
  return request.put<ApiResponse<AdminUser>>(`/admin/users/${userId}/role`, { role })
}

export function toggleUserActive(userId: string) {
  return request.put<ApiResponse<AdminUser>>(`/admin/users/${userId}/toggle-active`)
}

export function resetPassword(userId: string, new_password: string) {
  return request.post<ApiResponse<AdminUser>>(`/admin/users/${userId}/reset-password`, { new_password })
}

export function deleteUser(userId: string) {
  return request.delete<ApiResponse<null>>(`/admin/users/${userId}`)
}

export function getStats() {
  return request.get<ApiResponse<SystemStats>>('/admin/stats')
}

export function getSettings() {
  return request.get<ApiResponse<Record<string, string>>>('/admin/settings')
}

export function updateSettings(settings: Record<string, string>) {
  return request.put<ApiResponse<Record<string, string>>>('/admin/settings', { settings })
}

export function getSkills(page = 1, page_size = 20) {
  return request.get<ApiResponse<PaginatedSkills>>('/admin/skills', {
    params: { page, page_size },
  })
}

export function getSkill(skillId: string) {
  return request.get<ApiResponse<AdminSkill>>(`/admin/skills/${skillId}`)
}

export function createSkill(data: {
  name: string
  display_name: string
  description?: string
  version?: string
  author?: string
  config_schema?: string
}) {
  return request.post<ApiResponse<AdminSkill>>('/admin/skills', data)
}

export function updateSkill(skillId: string, data: {
  display_name?: string
  description?: string
  version?: string
  author?: string
  config_schema?: string
  is_enabled?: boolean
}) {
  return request.put<ApiResponse<AdminSkill>>(`/admin/skills/${skillId}`, data)
}

export function deleteSkill(skillId: string) {
  return request.delete<ApiResponse<null>>(`/admin/skills/${skillId}`)
}

export function toggleSkillEnabled(skillId: string) {
  return request.put<ApiResponse<AdminSkill>>(`/admin/skills/${skillId}/toggle-enabled`)
}

export function updateUserStatus(userId: string, is_active: boolean) {
  return request.put<ApiResponse<AdminUser>>(`/admin/users/${userId}/status`, { is_active })
}

export interface SystemConfig {
  llm_base_url: string
  llm_model: string
  llm_api_key: string
  anythingllm_base_url: string
  anythingllm_api_key: string
  cors_origins: string
}

export function getSystemConfig() {
  return request.get<ApiResponse<SystemConfig>>('/admin/config')
}

export function updateSystemConfig(config: Record<string, string>) {
  return request.put<ApiResponse<SystemConfig>>('/admin/config', config)
}

export function testLLMConnection(base_url: string, api_key: string, model: string) {
  return request.post<ApiResponse<{ status: string; message: string }>>('/admin/config/test-llm', { base_url, api_key, model })
}

export function testAnythingLLMConnection(base_url: string, api_key: string) {
  return request.post<ApiResponse<{ status: string; message: string }>>('/admin/config/test-anythingllm', { base_url, api_key })
}

export function getHealthCheck() {
  return request.get<ApiResponse<Record<string, { status: string; latency_ms: number }>>>('/admin/health')
}

// ── 审计日志 ──────────────────────────────────────────────

export interface AuditLog {
  id: string
  user_id: string
  user_email: string
  action: string
  resource_type: string | null
  resource_id: string | null
  detail: string | null
  ip_address: string | null
  created_at: string
}

export interface PaginatedAuditLogs {
  items: AuditLog[]
  total: number
  page: number
  page_size: number
}

export function getAuditLogs(page = 1, page_size = 20, action?: string, user_id?: string) {
  const params: Record<string, string | number> = { page, page_size }
  if (action) params.action = action
  if (user_id) params.user_id = user_id
  return request.get<ApiResponse<PaginatedAuditLogs>>('/admin/audit-logs', { params })
}
