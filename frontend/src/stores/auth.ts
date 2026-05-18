import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { User } from '../types'
import { login as apiLogin, register as apiRegister, getMe } from '../api/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const user = ref<User | null>(null)

  async function login(email: string, password: string) {
    const res = await apiLogin({ email, password })
    const data = res.data.data
    token.value = data.access_token
    localStorage.setItem('token', data.access_token)
    await fetchUser()
  }

  async function register(email: string, password: string) {
    const res = await apiRegister({ email, password })
    const data = res.data.data
    token.value = data.access_token
    localStorage.setItem('token', data.access_token)
    await fetchUser()
  }

    async function fetchUser() {
    try {
      const res = await getMe()
      if (res.data?.data) {
        user.value = res.data.data
      } else {
        logout()
      }
    } catch {
      logout()
    }
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
  }

  return { token, user, login, register, fetchUser, logout }
})
