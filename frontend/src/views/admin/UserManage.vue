<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h2 class="text-xl font-semibold text-gray-800">用户管理</h2>
    </div>

    <StatCards :stats="stats" />

    <div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div v-if="loading" class="p-12 text-center">
        <div class="inline-block w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
        <p class="text-gray-400 mt-4">加载中...</p>
      </div>

      <div v-else-if="users.length === 0" class="p-12 text-center">
                <svg class="w-12 h-12 mx-auto text-gray-300 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
        </svg>
        <p class="text-gray-400 text-lg">暂无用户数据</p>
      </div>

      <table v-else class="w-full">
        <thead class="bg-gray-50">
          <tr>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">邮箱</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">显示名</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">角色</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">状态</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">创建时间</th>
            <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">操作</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-200">
          <tr v-for="user in users" :key="user.id" class="hover:bg-gray-50 transition-colors">
            <td class="px-6 py-4 text-sm text-gray-900">{{ user.email }}</td>
            <td class="px-6 py-4 text-sm text-gray-600">{{ user.display_name || '-' }}</td>
            <td class="px-6 py-4">
                            <span
                class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
                :class="roleStyle(user.role)"
              >
                {{ roleLabel(user.role) }}
              </span>
            </td>
            <td class="px-6 py-4">
              <span
                class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
                :class="user.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'"
              >
                {{ user.is_active ? '启用' : '禁用' }}
              </span>
            </td>
            <td class="px-6 py-4 text-sm text-gray-500">{{ formatTime(user.created_at) }}</td>
            <td class="px-6 py-4 text-right">
              <div class="flex items-center justify-end gap-2">
                                <select
                  class="px-2 py-1.5 rounded-lg text-xs font-medium border border-gray-200 text-gray-600 bg-white hover:bg-gray-50 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                  :value="user.role"
                  @change="handleRoleChange(user, ($event.target as HTMLSelectElement).value)"
                >
                  <option value="member">成员</option>
                  <option value="auditor">审计员</option>
                  <option value="admin">管理员</option>
                </select>
                <button
                  class="px-3 py-1.5 rounded-lg text-xs font-medium transition-colors"
                  :class="user.is_active ? 'bg-yellow-50 text-yellow-600 hover:bg-yellow-100' : 'bg-green-50 text-green-600 hover:bg-green-100'"
                  @click="handleToggleActive(user)"
                >
                  {{ user.is_active ? '禁用' : '启用' }}
                </button>
                <button
                  class="px-3 py-1.5 rounded-lg text-xs font-medium bg-gray-50 text-gray-600 hover:bg-gray-100 transition-colors"
                  @click="openResetDialog(user)"
                >
                  重置密码
                </button>
                <button
                  class="px-3 py-1.5 rounded-lg text-xs font-medium bg-red-50 text-red-600 hover:bg-red-100 transition-colors"
                  @click="handleDelete(user)"
                >
                  删除
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="totalPages > 1" class="flex items-center justify-between px-6 py-4 border-t border-gray-200">
        <span class="text-sm text-gray-500">共 {{ total }} 条</span>
        <div class="flex items-center gap-2">
          <button
            class="px-3 py-1.5 rounded-lg text-sm border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors disabled:opacity-50"
            :disabled="page <= 1"
            @click="changePage(page - 1)"
          >
            上一页
          </button>
          <span class="text-sm text-gray-600">{{ page }} / {{ totalPages }}</span>
          <button
            class="px-3 py-1.5 rounded-lg text-sm border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors disabled:opacity-50"
            :disabled="page >= totalPages"
            @click="changePage(page + 1)"
          >
            下一页
          </button>
        </div>
      </div>
    </div>

        <div v-if="showResetDialog" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40" @click.self="showResetDialog = false">
      <div class="bg-white rounded-xl p-6 w-full max-w-md shadow-xl">
        <h3 class="text-lg font-semibold text-gray-900 mb-4">重置密码</h3>
        <p class="text-sm text-gray-500 mb-4">为 <span class="font-medium text-gray-700">{{ resetTarget?.email }}</span> 设置新密码</p>
        <input
          v-model="newPassword"
          type="password"
          placeholder="请输入新密码"
          class="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 mb-4"
        />
        <div class="flex justify-end gap-3">
          <button
            class="px-4 py-2 rounded-lg text-sm font-medium border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors"
            @click="showResetDialog = false"
          >
            取消
          </button>
          <button
            class="px-4 py-2 rounded-lg text-sm font-medium bg-blue-600 text-white hover:bg-blue-700 transition-colors"
            :disabled="!newPassword"
            @click="handleResetPassword"
          >
            确认重置
          </button>
        </div>
      </div>
    </div>

    <div v-if="toast" class="fixed top-6 right-6 z-[60] px-4 py-3 rounded-lg shadow-lg text-sm font-medium transition-all duration-300"
      :class="toast.type === 'success' ? 'bg-green-600 text-white' : 'bg-red-600 text-white'">
      {{ toast.message }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import StatCards from '../../components/StatCards.vue'
import { useAuthStore } from '../../stores/auth'
import { extractErrorMessage } from '../../api/request'
import {
  getUsers,
  getStats,
  updateUserRole,
  toggleUserActive,
  resetPassword,
  deleteUser,
} from '../../api/admin'
import type { AdminUser, SystemStats } from '../../api/admin'

const authStore = useAuthStore()

const users = ref<AdminUser[]>([])
const stats = ref<SystemStats | null>(null)
const loading = ref(true)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const totalPages = computed(() => Math.ceil(total.value / pageSize.value))

const showResetDialog = ref(false)
const resetTarget = ref<AdminUser | null>(null)
const newPassword = ref('')
const toast = ref<{ type: 'success' | 'error'; message: string } | null>(null)
let toastTimer: ReturnType<typeof setTimeout> | null = null

function showToast(type: 'success' | 'error', message: string) {
  if (toastTimer) clearTimeout(toastTimer)
  toast.value = { type, message }
  toastTimer = setTimeout(() => { toast.value = null }, 2500)
}

function formatTime(t: string) {
  if (!t) return '-'
  return new Date(t).toLocaleString('zh-CN')
}

async function fetchUsers() {
  loading.value = true
  try {
    const res = await getUsers(page.value, pageSize.value)
    users.value = res.data.data.items
    total.value = res.data.data.total
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

async function fetchStats() {
  try {
    const res = await getStats()
    stats.value = res.data.data
  } catch (e) {
    console.error(e)
  }
}

function changePage(p: number) {
  page.value = p
  fetchUsers()
}

function roleLabel(role: string) {
  if (role === 'admin') return '管理员'
  if (role === 'auditor') return '审计员'
  return '成员'
}

function roleStyle(role: string) {
  if (role === 'admin') return 'bg-purple-100 text-purple-800'
  if (role === 'auditor') return 'bg-amber-100 text-amber-800'
  return 'bg-gray-100 text-gray-600'
}

async function handleRoleChange(user: AdminUser, newRole: string) {
  if (user.id === authStore.user?.id) {
    showToast('error', '不能修改当前登录账户的角色')
    return
  }
    if (user.role === newRole) return
  if (!confirm(`确定将用户 "${user.email}" 的角色更改为 ${roleLabel(newRole)}？`)) return
  try {
    await updateUserRole(user.id, newRole)
    showToast('success', '角色已更新')
    fetchUsers()
    } catch (e: unknown) {
    showToast('error', extractErrorMessage(e, '操作失败'))
  }
}

async function handleToggleActive(user: AdminUser) {
  if (user.id === authStore.user?.id) {
    showToast('error', '不能禁用当前登录账户')
    return
  }
  try {
    await toggleUserActive(user.id)
    showToast('success', '状态已更新')
    fetchUsers()
    } catch (e: unknown) {
    showToast('error', extractErrorMessage(e, '操作失败'))
  }
}

function openResetDialog(user: AdminUser) {
  resetTarget.value = user
  newPassword.value = ''
  showResetDialog.value = true
}

async function handleResetPassword() {
  if (!resetTarget.value || !newPassword.value) return
  try {
    await resetPassword(resetTarget.value.id, newPassword.value)
    showToast('success', '密码已重置')
    showResetDialog.value = false
    resetTarget.value = null
    newPassword.value = ''
    } catch (e: unknown) {
    showToast('error', extractErrorMessage(e, '重置失败'))
  }
}

async function handleDelete(user: AdminUser) {
  if (user.id === authStore.user?.id) {
    showToast('error', '不能删除当前登录账户')
    return
  }
  if (!confirm(`确定要删除用户 "${user.email}" 吗？此操作不可恢复。`)) return
  try {
    await deleteUser(user.id)
    showToast('success', '用户已删除')
    if (users.value.length === 1 && page.value > 1) {
      page.value--
    }
    fetchUsers()
    fetchStats()
    } catch (e: unknown) {
    showToast('error', extractErrorMessage(e, '删除失败'))
  }
}

onMounted(() => {
  fetchUsers()
  fetchStats()
})

onUnmounted(() => {
  if (toastTimer) clearTimeout(toastTimer)
})
</script>
