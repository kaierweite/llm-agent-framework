import request from './request'
import type { LoginRequest, RegisterRequest, AuthResponse, ApiResponse, User } from '../types'

export function login(data: LoginRequest) {
  return request.post<ApiResponse<AuthResponse['data']>>('/auth/login', data)
}

export function register(data: RegisterRequest) {
  return request.post<ApiResponse<AuthResponse['data']>>('/auth/register', data)
}

export function getMe() {
  return request.get<ApiResponse<User>>('/auth/me')
}

export function updateProfile(data: { display_name?: string; avatar_url?: string }) {
  return request.put<ApiResponse<User>>('/user/me', data)
}

export function changePassword(data: { old_password: string; new_password: string }) {
  return request.post<ApiResponse<null>>('/user/me/change-password', data)
}
