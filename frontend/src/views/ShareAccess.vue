<template>
  <div class="min-h-screen bg-gradient-to-br from-slate-50 via-white to-indigo-50/30">
    <div class="max-w-2xl mx-auto px-6 py-16">
      <!-- Header -->
      <div class="text-center mb-10">
        <div class="w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center mx-auto mb-4 shadow-lg shadow-indigo-200">
          <svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
          </svg>
        </div>
        <h1 class="text-2xl font-bold bg-gradient-to-r from-gray-900 to-gray-600 bg-clip-text text-transparent">凭码访问</h1>
        <p class="text-sm text-gray-400 mt-2">输入分享码，查看他人分享的知识库</p>
      </div>

      <!-- Input Card -->
      <div class="bg-white/80 backdrop-blur-sm rounded-2xl shadow-sm border border-gray-100 p-6 mb-6">
        <label class="block text-sm font-medium text-gray-700 mb-2">分享码</label>
        <div class="flex gap-2">
          <input
            v-model="inputCode"
            type="text"
            class="flex-1 px-4 py-3 border border-gray-200 rounded-xl text-sm font-mono tracking-wider uppercase focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 outline-none transition-all bg-gray-50 focus:bg-white"
            placeholder="请输入 8 位分享码"
            maxlength="8"
            @keyup.enter="handleAccess"
          />
          <button
            class="px-6 py-3 rounded-xl text-sm font-medium text-white bg-gradient-to-r from-indigo-500 to-purple-500 hover:from-indigo-600 hover:to-purple-600 shadow-md shadow-indigo-200/50 hover:shadow-lg hover:shadow-indigo-200 transition-all duration-200 active:scale-[0.98] whitespace-nowrap"
            :disabled="!inputCode.trim() || accessing"
            @click="handleAccess"
          >
            <span v-if="accessing" class="flex items-center gap-1.5">
              <svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
              验证中
            </span>
            <span v-else>访问</span>
          </button>
        </div>
        <p v-if="errorMsg" class="mt-3 text-sm text-red-500 flex items-center gap-1.5">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
          {{ errorMsg }}
        </p>
      </div>

      <!-- Result Card -->
      <Transition name="modal">
        <div v-if="sharedKb" class="bg-white/80 backdrop-blur-sm rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
          <div class="bg-gradient-to-r from-indigo-500/5 to-purple-500/5 px-6 py-5 border-b border-gray-100">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center text-white text-sm font-bold">
                {{ sharedKb.name.charAt(0).toUpperCase() }}
              </div>
              <div>
                <h2 class="text-lg font-bold text-gray-900">{{ sharedKb.name }}</h2>
                <p v-if="sharedKb.description" class="text-sm text-gray-400 mt-0.5">{{ sharedKb.description }}</p>
              </div>
            </div>
          </div>
          <div class="p-6">
            <div class="flex items-center gap-4 text-sm text-gray-500">
              <span class="flex items-center gap-1.5">
                <svg class="w-4 h-4 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
                </svg>
                权限：{{ sharedKb.permission === 'query' ? '可问答' : '只读' }}
              </span>
              <span class="flex items-center gap-1.5">
                <svg class="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                访问于 {{ formatTime(sharedKb.accessed_at) }}
              </span>
            </div>

            <div class="mt-6 pt-4 border-t border-gray-100">
              <p class="text-sm text-gray-500 mb-3">你可以：</p>
              <div class="flex gap-2">
                                <router-link
                  :to="{ path: '/', query: { sharedKbId: sharedKb.id, sharedKbName: sharedKb.name, sharedKbPermission: sharedKb.permission } }"
                  class="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium text-white bg-gradient-to-r from-indigo-500 to-purple-500 hover:from-indigo-600 hover:to-purple-600 shadow-md shadow-indigo-200/50 transition-all active:scale-[0.98]"
                >
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                  </svg>
                  开始对话
                </router-link>
                <button
                  class="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium text-gray-600 bg-gray-100 hover:bg-gray-200 transition-all active:scale-[0.98]"
                  @click="reset"
                >
                  输入另一个分享码
                </button>
              </div>
            </div>
          </div>
        </div>
      </Transition>
    </div>

    <!-- Toast -->
    <Teleport to="body">
      <Transition name="toast">
        <div v-if="toast" class="fixed top-6 right-6 z-[100] flex items-center gap-3 px-5 py-3.5 rounded-xl shadow-xl text-sm font-medium backdrop-blur-sm"
          :class="{
            'bg-emerald-500/90 text-white': toast.type === 'success',
            'bg-red-500/90 text-white': toast.type === 'error',
          }"
        >
          <svg v-if="toast.type === 'success'" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          {{ toast.message }}
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { accessByShareCode } from '@/api/kbShare'
import type { SharedKnowledgeBase } from '@/types'

const inputCode = ref('')
const accessing = ref(false)
const errorMsg = ref('')
const sharedKb = ref<SharedKnowledgeBase | null>(null)
const toast = ref<{ type: string; message: string } | null>(null)

function showToast(type: string, message: string) {
  toast.value = { type, message }
  setTimeout(() => { toast.value = null }, 3000)
}

function formatTime(iso: string) {
  return new Date(iso).toLocaleString('zh-CN')
}

async function handleAccess() {
  const code = inputCode.value.trim()
  if (!code) return

  accessing.value = true
  errorMsg.value = ''
  sharedKb.value = null

  try {
    const res = await accessByShareCode(code)
    sharedKb.value = res.data.data
    showToast('success', `已访问知识库：${res.data.data.name}`)
  } catch (err: unknown) {
    const e = err as { response?: { data?: { detail?: { message?: string } | string } } }
    const detail = e.response?.data?.detail
    if (detail && typeof detail === 'object' && detail.message) {
      errorMsg.value = detail.message
    } else if (typeof detail === 'string') {
      errorMsg.value = detail
    } else {
      errorMsg.value = '分享码无效或已过期'
    }
  } finally {
    accessing.value = false
  }
}

function reset() {
  inputCode.value = ''
  sharedKb.value = null
  errorMsg.value = ''
}
</script>

<style scoped>
.modal-enter-active,
.modal-leave-active {
  transition: all 0.3s ease;
}
.modal-enter-from,
.modal-leave-to {
  opacity: 0;
  transform: translateY(10px);
}

.toast-enter-active {
  transition: all 0.3s cubic-bezier(0.21, 1.02, 0.73, 1);
}
.toast-leave-active {
  transition: all 0.15s ease;
}
.toast-enter-from {
  opacity: 0;
  transform: translateX(30px) scale(0.95);
}
.toast-leave-to {
  opacity: 0;
  transform: translateX(30px) scale(0.95);
}
</style>
