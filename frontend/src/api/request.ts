import axios from 'axios'
import { useAuthStore } from '../stores/auth'
import router from '../router'

const request = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

// 请求拦截器：自动带上 token
request.interceptors.request.use((config) => {
  const authStore = useAuthStore()
  if (authStore.token) {
    config.headers.Authorization = `Bearer ${authStore.token}`
  }
  return config
})

// 响应拦截器：统一处理错误
request.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status

    // 401 → 清理登录态并跳转（登录页自身请求不触发跳转，避免竞态）
    if (status === 401 && router.currentRoute.value.path !== '/login') {
      const authStore = useAuthStore()
      authStore.logout()
      router.push('/login')
    }

    return Promise.reject(error)
  }
)

/**
 * 从 axios 错误中提取用户可读的错误消息。
 * 优先使用后端返回的 detail.message，其次用 HTTP 状态码映射。
 */
export function extractErrorMessage(err: unknown, fallback = '操作失败'): string {
  if (!err || typeof err !== 'object') return fallback
  const e = err as { response?: { data?: { detail?: { message?: string } | string }; status?: number }; message?: string }

  // 后端返回的结构化错误
  const detail = e.response?.data?.detail
  if (detail) {
    if (typeof detail === 'string') return detail
    if (detail.message) return detail.message
  }

  // HTTP 状态码映射
  const status = e.response?.status
  if (status === 403) return '没有权限执行此操作'
  if (status === 404) return '请求的资源不存在'
  if (status === 429) return '请求过于频繁，请稍后再试'
  if (status === 500) return '服务器内部错误'
  if (status === 502) return '服务暂时不可用，请稍后再试'
  if (status === 503) return '服务暂时不可用，请稍后再试'

  // 网络错误
  if (e.message?.includes('Network Error') || e.message?.includes('ERR_NETWORK')) return '网络连接失败，请检查网络'
  if (e.message?.includes('timeout')) return '请求超时，请稍后再试'

  return e.message || fallback
}

export default request
