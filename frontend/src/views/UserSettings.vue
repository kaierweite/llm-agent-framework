<template>
  <div class="min-h-screen bg-gray-50">
    <!-- 顶部导航 -->
    <header class="h-14 bg-white border-b border-gray-200 flex items-center px-6 shrink-0">
      <button
        @click="router.push('/')"
        class="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition text-sm"
      >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
        </svg>
        返回对话
      </button>
      <h2 class="ml-4 text-base font-medium text-gray-800">个人中心</h2>
    </header>

    <div class="max-w-2xl mx-auto py-8 px-6 space-y-6">
      <!-- 基本信息 -->
      <div class="bg-white rounded-xl border border-gray-200 p-6">
        <h3 class="text-lg font-medium text-gray-900 mb-4">基本信息</h3>

        <!-- 头像 -->
        <div class="flex items-center gap-4 mb-6">
          <div class="w-16 h-16 rounded-full bg-blue-600 flex items-center justify-center text-white text-xl font-medium">
            {{ avatarText }}
          </div>
          <div>
            <p class="text-sm text-gray-500">当前头像</p>
            <p class="text-xs text-gray-400 mt-1">根据昵称或邮箱自动生成</p>
          </div>
        </div>

        <!-- 昵称 -->
        <div class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">昵称</label>
            <div class="flex gap-2">
              <input
                v-model="displayName"
                type="text"
                placeholder="设置你的昵称"
                class="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition"
              />
              <button
                @click="handleSaveProfile"
                :disabled="savingProfile"
                class="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50 transition"
              >
                {{ savingProfile ? '保存中...' : '保存' }}
              </button>
            </div>
            <p v-if="profileMsg" :class="['text-xs mt-1', profileMsgType === 'success' ? 'text-green-600' : 'text-red-600']">
              {{ profileMsg }}
            </p>
          </div>

          <!-- 邮箱（只读） -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">邮箱</label>
            <input
              :value="authStore.user?.email"
              type="email"
              disabled
              class="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm bg-gray-50 text-gray-500 cursor-not-allowed"
            />
            <p class="text-xs text-gray-400 mt-1">邮箱不可修改</p>
          </div>

                    <!-- 角色 -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">角色</label>
            <span :class="[
              'inline-block px-2.5 py-1 rounded-full text-xs font-medium',
              authStore.user?.role === 'admin' ? 'bg-purple-100 text-purple-700' : authStore.user?.role === 'auditor' ? 'bg-amber-100 text-amber-700' : 'bg-gray-100 text-gray-600'
            ]">
              {{ authStore.user?.role === 'admin' ? '管理员' : authStore.user?.role === 'auditor' ? '审计员' : '普通用户' }}
            </span>
          </div>

          <!-- 所属部门 -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">所属部门</label>
            <p class="text-sm text-gray-600">{{ authStore.user?.department_name || '未分配部门' }}</p>
          </div>

          <!-- 注册时间 -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">注册时间</label>
            <p class="text-sm text-gray-600">{{ formatDate(authStore.user?.created_at) }}</p>
          </div>
        </div>
      </div>

      <!-- 修改密码 -->
      <div class="bg-white rounded-xl border border-gray-200 p-6">
        <h3 class="text-lg font-medium text-gray-900 mb-4">修改密码</h3>

        <div class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">当前密码</label>
            <input
              v-model="oldPassword"
              type="password"
              placeholder="输入当前密码"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">新密码</label>
            <input
              v-model="newPassword"
              type="password"
              placeholder="至少 8 位"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">确认新密码</label>
            <input
              v-model="confirmPassword"
              type="password"
              placeholder="再次输入新密码"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition"
            />
          </div>

          <div class="flex items-center gap-3">
            <button
              @click="handleChangePassword"
              :disabled="savingPassword"
              class="px-4 py-2 bg-gray-900 text-white text-sm rounded-lg hover:bg-gray-800 disabled:opacity-50 transition"
            >
              {{ savingPassword ? '修改中...' : '修改密码' }}
            </button>
            <p v-if="passwordMsg" :class="['text-xs', passwordMsgType === 'success' ? 'text-green-600' : 'text-red-600']">
              {{ passwordMsg }}
            </p>
          </div>
        </div>
      </div>

      <!-- 账号信息 -->
      <div class="bg-white rounded-xl border border-gray-200 p-6">
        <h3 class="text-lg font-medium text-gray-900 mb-4">账号信息</h3>
        <div class="text-sm text-gray-600 space-y-2">
          <p>用户 ID：<code class="bg-gray-100 px-1.5 py-0.5 rounded text-xs">{{ authStore.user?.id }}</code></p>
          <p>角色：<span class="font-medium">{{ authStore.user?.role === 'admin' ? '管理员' : '普通用户' }}</span></p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { updateProfile, changePassword } from '../api/auth'
import { extractErrorMessage } from '../api/request'

const router = useRouter()
const authStore = useAuthStore()

// 基本信息
const displayName = ref('')
const savingProfile = ref(false)
const profileMsg = ref('')
const profileMsgType = ref<'success' | 'error'>('success')

// 修改密码
const oldPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const savingPassword = ref(false)
const passwordMsg = ref('')
const passwordMsgType = ref<'success' | 'error'>('success')

const avatarText = computed(() => {
  const name = authStore.user?.display_name || authStore.user?.email || '?'
  return name.charAt(0).toUpperCase()
})

function formatDate(dateStr?: string) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('zh-CN', {
    year: 'numeric', month: 'long', day: 'numeric'
  })
}

onMounted(async () => {
  if (!authStore.user) {
    try { await authStore.fetchUser() } catch { router.push('/login'); return }
  }
  displayName.value = authStore.user?.display_name || ''
})

async function handleSaveProfile() {
  savingProfile.value = true
  profileMsg.value = ''
  try {
    const res = await updateProfile({ display_name: displayName.value.trim() || undefined })
    if (res.data.code === 0) {
      // 更新 store 中的用户信息
      authStore.user = res.data.data
      profileMsg.value = '保存成功'
      profileMsgType.value = 'success'
    } else {
      profileMsg.value = res.data.message || '保存失败'
      profileMsgType.value = 'error'
    }
    } catch (e: unknown) {
    profileMsg.value = extractErrorMessage(e, '保存失败')
    profileMsgType.value = 'error'
  } finally {
    savingProfile.value = false
  }
}

async function handleChangePassword() {
  passwordMsg.value = ''

  if (!oldPassword.value) {
    passwordMsg.value = '请输入当前密码'
    passwordMsgType.value = 'error'
    return
  }
  if (newPassword.value.length < 8) {
    passwordMsg.value = '新密码至少 8 位'
    passwordMsgType.value = 'error'
    return
  }
  if (newPassword.value !== confirmPassword.value) {
    passwordMsg.value = '两次输入的密码不一致'
    passwordMsgType.value = 'error'
    return
  }

  savingPassword.value = true
  try {
    const res = await changePassword({
      old_password: oldPassword.value,
      new_password: newPassword.value,
    })
    if (res.data.code === 0) {
      passwordMsg.value = '密码修改成功'
      passwordMsgType.value = 'success'
      oldPassword.value = ''
      newPassword.value = ''
      confirmPassword.value = ''
    } else {
      passwordMsg.value = res.data.message || '修改失败'
      passwordMsgType.value = 'error'
    }
    } catch (e: unknown) {
    passwordMsg.value = extractErrorMessage(e, '修改失败')
    passwordMsgType.value = 'error'
  } finally {
    savingPassword.value = false
  }
}
</script>
