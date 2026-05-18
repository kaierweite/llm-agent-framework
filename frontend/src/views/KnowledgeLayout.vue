<template>
  <div class="h-screen flex flex-col bg-gray-100">
    <header class="h-14 bg-gray-900 flex items-center px-6 shrink-0">
      <h1 class="text-white font-medium text-base">知识库管理</h1>
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

    <main class="flex-1 overflow-y-auto p-6">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()
</script>
