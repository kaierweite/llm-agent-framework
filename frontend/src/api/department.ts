import request from './request'
import type { ApiResponse } from '../types'

export interface Department {
  id: string
  name: string
  code: string
  description: string | null
  parent_id: string | null
  leader_id: string | null
  leader_email: string | null
  sort_order: number
  is_active: boolean
  member_count: number
  children?: Department[]
  created_at: string
  updated_at: string
}

export interface DepartmentCreate {
  name: string
  code: string
  description?: string
  parent_id?: string | null
  leader_id?: string | null
  sort_order?: number
}

export interface DepartmentUpdate {
  name?: string
  code?: string
  description?: string
  parent_id?: string | null
  leader_id?: string | null
  sort_order?: number
  is_active?: boolean
}

export interface DepartmentMember {
  id: string
  email: string
  display_name: string | null
  role: string
  is_active: boolean
  created_at: string
}

export interface PaginatedMembers {
  items: DepartmentMember[]
  total: number
  page: number
  page_size: number
}

export function getDepartmentTree() {
  return request.get<ApiResponse<Department[]>>('/departments/tree')
}

export function getDepartment(id: string) {
  return request.get<ApiResponse<Department>>(`/departments/${id}`)
}

export function createDepartment(data: DepartmentCreate) {
  return request.post<ApiResponse<Department>>('/departments', data)
}

export function updateDepartment(id: string, data: DepartmentUpdate) {
  return request.put<ApiResponse<Department>>(`/departments/${id}`, data)
}

export function deleteDepartment(id: string) {
  return request.delete<ApiResponse<null>>(`/departments/${id}`)
}

export function getDepartmentMembers(id: string) {
  return request.get<ApiResponse<PaginatedMembers>>(`/departments/${id}/members`)
}

export function addDepartmentMember(id: string, userId: string) {
  return request.post<ApiResponse<null>>(`/departments/${id}/members`, { user_id: userId })
}

export function removeDepartmentMember(id: string, userId: string) {
  return request.delete<ApiResponse<null>>(`/departments/${id}/members/${userId}`)
}
