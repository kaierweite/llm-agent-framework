<template>
  <div class="h-screen flex flex-col bg-gray-100">
    <header class="h-14 bg-gray-900 flex items-center px-6 shrink-0">
      <h1 class="text-white font-medium text-base">企业管理后台</h1>
      <router-link to="/" class="ml-auto flex items-center gap-1.5 text-gray-400 hover:text-white text-sm transition">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
        </svg>
        返回对话
      </router-link>
      <div class="ml-4 flex items-center gap-2 text-gray-400 text-sm">
        <div class="w-6 h-6 rounded-full bg-blue-600 flex items-center justify-center text-white text-xs font-medium">
          {{ authStore.user?.email?.split('@')[0]?.toUpperCase() || '?' }}
        </div>
        <span>{{ authStore.user?.email }}</span>
      </div>
    </header>

    <div class="flex flex-1 overflow-hidden">
      <nav class="w-56 bg-white border-r border-gray-200 py-4 shrink-0">
        <router-link
          to="/admin/users"
          class="flex items-center gap-3 px-5 py-2.5 text-sm transition"
          :class="route.path === '/admin/users' ? 'text-blue-600 bg-blue-50 font-medium' : 'text-gray-600 hover:bg-gray-50'"
        >
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
          </svg>
                    用户管理
        </router-link>
        <router-link
          to="/admin/departments"
          class="flex items-center gap-3 px-5 py-2.5 text-sm transition"
          :class="route.path === '/admin/departments' ? 'text-blue-600 bg-blue-50 font-medium' : 'text-gray-600 hover:bg-gray-50'"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" /></svg>
          部门管理
        </router-link>
        <router-link
          to="/admin/knowledge"
          class="flex items-center gap-3 px-5 py-2.5 text-sm transition"
          :class="route.path === '/admin/knowledge' ? 'text-blue-600 bg-blue-50 font-medium' : 'text-gray-600 hover:bg-gray-50'"
        >
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
          </svg>
          知识库管理
        </router-link>
        <router-link
          to="/admin/settings"
          class="flex items-center gap-3 px-5 py-2.5 text-sm transition"
          :class="route.path === '/admin/settings' ? 'text-blue-600 bg-blue-50 font-medium' : 'text-gray-600 hover:bg-gray-50'"
        >
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
                    系统设置
        </router-link>
        <router-link
          to="/admin/audit-logs"
          class="flex items-center gap-3 px-5 py-2.5 text-sm transition"
          :class="route.path === '/admin/audit-logs' ? 'text-blue-600 bg-blue-50 font-medium' : 'text-gray-600 hover:bg-gray-50'"
        >
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          审计日志
        </router-link>
      </nav>

      <main class="flex-1 overflow-y-auto p-6">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

onMounted(() => {
  if (!authStore.user) {
    authStore.fetchUser().then(() => {
      if (!['admin', 'auditor'].includes(authStore.user?.role || '')) {
        router.replace('/')
      }
    }).catch(() => {
      router.replace('/')
    })
  } else if (!['admin', 'auditor'].includes(authStore.user.role)) {
    router.replace('/')
  }
})
</script>
