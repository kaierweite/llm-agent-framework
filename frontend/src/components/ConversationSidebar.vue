<template>
  <aside class="w-72 bg-gray-900 flex flex-col">
    <div class="p-3">
      <button
        @click="$emit('new-conversation')"
        class="w-full flex items-center gap-2 px-4 py-2.5 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition text-sm"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
        </svg>
        新建对话
      </button>
    </div>

    <!-- 搜索框 -->
    <div class="px-3 pb-2">
      <div class="relative">
        <svg class="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        <input
          :value="searchQuery"
          @input="$emit('update:searchQuery', ($event.target as HTMLInputElement).value)"
          type="text"
          aria-label="搜索消息内容"
          placeholder="搜索消息内容..."
          class="w-full pl-9 pr-8 py-2 bg-gray-800 text-gray-300 text-sm rounded-lg border border-gray-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none placeholder-gray-500 transition"
        />
        <button
          v-if="searchQuery"
          @click="$emit('clear-search')"
          class="absolute right-2 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300 transition"
          title="清除搜索"
          aria-label="清除搜索"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg>
        </button>
      </div>
    </div>

    <!-- 搜索结果面板 -->
    <div v-if="searchQuery.trim() && !searchLoading" class="flex-1 overflow-y-auto px-2 space-y-1">
      <div v-if="searchResults.length === 0" class="px-3 py-6 text-center text-gray-500 text-sm">
        未找到匹配的消息
      </div>
      <template v-else>
        <p class="text-xs text-gray-500 font-medium px-3 pt-3 pb-1">搜索结果（{{ searchTotal }} 条对话）</p>
        <div
          v-for="item in searchResults"
          :key="item.conversation_id"
          class="px-3 py-2 rounded-lg cursor-pointer transition text-sm text-gray-300 hover:bg-gray-800"
          @click="$emit('search-result-click', item)"
        >
          <div class="font-medium text-gray-200 truncate mb-1">{{ item.conversation_title }}</div>
          <div
            v-for="msg in item.messages"
            :key="msg.id"
            class="text-xs text-gray-400 truncate leading-relaxed"
          >
            <span class="text-gray-500">{{ msg.role === 'user' ? '👤' : '🤖' }}</span>
            <span v-html="msg.highlight"></span>
          </div>
        </div>
      </template>
    </div>
    <div v-else-if="searchQuery.trim() && searchLoading" class="flex-1 flex items-center justify-center">
      <span class="text-gray-500 text-sm">搜索中...</span>
    </div>

    <!-- 对话列表 -->
    <div v-if="!searchQuery.trim()" class="flex-1 overflow-y-auto px-2 space-y-1">
      <template v-for="group in groups" :key="group.label">
        <p class="text-xs text-gray-500 font-medium px-3 pt-3 pb-1">{{ group.label }}</p>
        <div
          v-for="conv in group.items"
          :key="conv.id"
          @click="$emit('select-conversation', conv)"
          class="group flex items-center gap-2 px-3 py-2.5 rounded-lg cursor-pointer transition text-sm"
          :class="currentConversationId === conv.id ? 'bg-gray-700 text-white' : 'text-gray-300 hover:bg-gray-800'"
        >
          <svg class="w-4 h-4 shrink-0 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
          </svg>
          <span class="truncate flex-1">{{ conv.title }}</span>
          <div class="hidden group-hover:flex items-center gap-1">
            <button @click.stop="$emit('rename', conv)" class="p-1 hover:bg-gray-600 rounded transition" title="重命名" aria-label="重命名对话">
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
            </button>
            <button @click.stop="$emit('export-md', conv)" class="p-1 hover:bg-gray-600 rounded transition" title="导出 Markdown" aria-label="导出对话为 Markdown">
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </button>
            <button @click.stop="$emit('delete', conv)" class="p-1 hover:bg-red-600 rounded transition" title="删除" aria-label="删除对话">
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          </div>
        </div>
      </template>
    </div>

    <!-- 底部导航 -->
    <div class="p-3 border-t border-gray-700 space-y-2">
      <router-link
        v-if="isAdmin"
        to="/admin"
        class="flex items-center gap-2 px-3 py-2 text-sm text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
                管理后台
      </router-link>
            <router-link
        to="/knowledge"
        class="flex items-center gap-2 px-3 py-2 text-sm text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
        </svg>
        知识库
      </router-link>
      <router-link
        to="/share-access"
        class="flex items-center gap-2 px-3 py-2 text-sm text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
        </svg>
        凭码访问
      </router-link>
      <router-link
        to="/settings"
        class="flex items-center gap-2 px-3 py-2 text-sm text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
        </svg>
        个人中心
      </router-link>
      <div class="flex items-center gap-2 text-gray-400 text-sm">
        <div class="w-7 h-7 rounded-full bg-blue-600 flex items-center justify-center text-white text-xs font-medium">
          {{ userEmail?.split('@')[0]?.toUpperCase() || '?' }}
        </div>
        <span class="flex-1 truncate">{{ userEmail || '未登录' }}</span>
        <button @click="$emit('logout')" class="p-1 hover:text-white transition" title="退出登录" aria-label="退出登录">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
          </svg>
        </button>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Conversation, SearchResultItem } from '../types'

const props = defineProps<{
  conversations: Conversation[]
  currentConversationId: string | null
  searchQuery: string
  searchResults: SearchResultItem[]
  searchTotal: number
  searchLoading: boolean
  isAdmin: boolean
  userEmail: string | null
}>()

defineEmits<{
  'new-conversation': []
  'select-conversation': [conv: Conversation]
  'rename': [conv: Conversation]
  'delete': [conv: Conversation]
  'export-md': [conv: Conversation]
  'search-result-click': [item: SearchResultItem]
  'update:searchQuery': [value: string]
  'clear-search': []
  'logout': []
}>()

function isSameDay(d1: Date, d2: Date) {
  return d1.getFullYear() === d2.getFullYear() && d1.getMonth() === d2.getMonth() && d1.getDate() === d2.getDate()
}

function isYesterday(date: Date) {
  const yesterday = new Date()
  yesterday.setDate(yesterday.getDate() - 1)
  return isSameDay(date, yesterday)
}

const groups = computed(() => {
  const query = props.searchQuery.toLowerCase().trim()
  const filtered = query
    ? props.conversations.filter((c) => c.title.toLowerCase().includes(query))
    : props.conversations

  const today: Conversation[] = []
  const yesterday: Conversation[] = []
  const earlier: Conversation[] = []
  const now = new Date()

  for (const conv of filtered) {
    const d = new Date(conv.updated_at)
    if (isSameDay(d, now)) {
      today.push(conv)
    } else if (isYesterday(d)) {
      yesterday.push(conv)
    } else {
      earlier.push(conv)
    }
  }

  const result: { label: string; items: Conversation[] }[] = []
  if (today.length > 0) result.push({ label: '今天', items: today })
  if (yesterday.length > 0) result.push({ label: '昨天', items: yesterday })
  if (earlier.length > 0) result.push({ label: '更早', items: earlier })
  return result
})
</script>
