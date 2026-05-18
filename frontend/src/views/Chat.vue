<template>
  <div class="h-screen flex bg-gray-100">
    <ConversationSidebar
      :conversations="chatStore.conversations"
      :current-conversation-id="chatStore.currentConversation?.id ?? null"
      v-model:search-query="searchQuery"
      :search-results="searchResults"
      :search-total="searchTotal"
      :search-loading="searchLoading"
      :is-admin="authStore.user?.role === 'admin' || authStore.user?.role === 'auditor'"
      :user-email="authStore.user?.email ?? null"
      @new-conversation="handleNewConversation"
      @select-conversation="handleSelectConversation"
      @rename="handleRename"
      @delete="handleDelete"
      @export-md="handleExportMarkdown"
      @search-result-click="handleSearchResultClick"
      @clear-search="clearSearch"
      @logout="handleLogout"
    />

    <main class="flex-1 flex flex-col">
            <header class="h-14 bg-white border-b border-gray-200 flex items-center px-6 shrink-0">
        <h2 class="text-base font-medium text-gray-800 truncate">
          {{ chatStore.currentConversation?.title || '选择或新建一个对话' }}
        </h2>
        
      </header>

      <div ref="messagesContainer" class="flex-1 overflow-y-auto px-6 py-4 space-y-4" @scroll="checkScrollPosition">
        <div v-if="!chatStore.currentConversation" class="h-full flex items-center justify-center">
          <div class="text-center text-gray-400">
            <svg class="w-16 h-16 mx-auto mb-4 opacity-30" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
            </svg>
            <p class="text-lg">开始一个新的对话</p>
            <p class="text-sm mt-1">在左侧点击"新建对话"开始</p>
          </div>
        </div>

        <template v-else>
          <MessageItem
            v-for="msg in chatStore.messages"
            :key="msg.id"
            :msg="msg"
            :is-editing="editingMessageId === msg.id"
            :editing-content="editingMessageId === msg.id ? editingContent : ''"
            :feedback-submitting="feedbackSubmitting === msg.id"
            :is-streaming="!!chatStore.streamingContent"
            @start-edit="startEdit"
            @cancel-edit="cancelEdit"
            @confirm-edit="confirmEdit"
            @feedback="handleFeedback"
            @regenerate="handleRegenerate"
          />

          <!-- 流式输出 -->
          <div v-if="chatStore.streamingContent" class="flex flex-col gap-2 items-start">
            <div class="max-w-[70%] px-4 py-3 rounded-2xl rounded-bl-md bg-white text-gray-800 border border-gray-200 shadow-sm text-sm leading-relaxed whitespace-pre-wrap">
              {{ cleanContent(chatStore.streamingContent) }}
              <span class="inline-block w-1.5 h-4 bg-gray-400 ml-0.5 animate-pulse rounded-sm"></span>
            </div>
          </div>
        </template>
      </div>

      <div v-if="chatStore.currentConversation" class="border-t border-gray-200 bg-white px-6 py-3 shrink-0">
        <div class="mb-2">
          <KnowledgeBaseSelector />
        </div>
        <form @submit.prevent="handleSend" class="flex gap-3">
          <input
            v-model="inputText"
            type="text"
            :disabled="!!chatStore.streamingContent"
            class="flex-1 px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition disabled:opacity-50"
            placeholder="输入你的问题..."
            aria-label="输入消息"
          />
          <button
            type="submit"
            :disabled="!inputText.trim() || !!chatStore.streamingContent"
            class="px-5 py-2.5 bg-blue-600 text-white rounded-xl font-medium hover:bg-blue-700 disabled:opacity-50 transition flex items-center gap-2"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
            发送
          </button>
        </form>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useChatStore } from '../stores/chat'
import { useKnowledgeStore } from '../stores/knowledge'
import type { Conversation, Message, SearchResultItem } from '../types'
import { searchMessages, exportConversationMarkdown, submitFeedback } from '../api/chat'
import ConversationSidebar from '../components/ConversationSidebar.vue'
import MessageItem from '../components/MessageItem.vue'
import KnowledgeBaseSelector from '../components/KnowledgeBaseSelector.vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const chatStore = useChatStore()
const knowledgeStore = useKnowledgeStore()

const inputText = ref('')
const searchQuery = ref('')
const messagesContainer = ref<HTMLElement | null>(null)
const isUserNearBottom = ref(true)
const searchResults = ref<SearchResultItem[]>([])
const searchTotal = ref(0)
const searchLoading = ref(false)
let searchDebounceTimer: ReturnType<typeof setTimeout> | null = null

// ── 消息编辑 ──
const editingMessageId = ref<string | null>(null)
const editingContent = ref('')

function startEdit(msg: Message) {
  editingMessageId.value = msg.id
  editingContent.value = msg.content
}

function cancelEdit() {
  editingMessageId.value = null
  editingContent.value = ''
}

function confirmEdit(messageId: string, content: string) {
  editingMessageId.value = null
  editingContent.value = ''
  chatStore.editAndResend(messageId, content)
}

function handleRegenerate(messageId: string) {
  chatStore.regenerateMessage(messageId)
}

// ── 消息反馈 ──
const feedbackSubmitting = ref<string | null>(null)

async function handleFeedback(msg: Message, type: 'up' | 'down') {
  if (!chatStore.currentConversation) return
  const convId = chatStore.currentConversation.id
  const newFeedback = msg.feedback === type ? null : type
  feedbackSubmitting.value = msg.id
  try {
    await submitFeedback(convId, msg.id, newFeedback)
    msg.feedback = newFeedback
  } catch (e) {
    console.error('反馈提交失败', e)
  } finally {
    feedbackSubmitting.value = null
  }
}

function checkScrollPosition() {
  const el = messagesContainer.value
  if (!el) return
  isUserNearBottom.value = el.scrollHeight - el.scrollTop - el.clientHeight < 100
}

onMounted(async () => {
  if (authStore.token && !authStore.user) {
    await authStore.fetchUser()
  }
  await chatStore.loadConversations()

    // 处理从分享码页面跳转过来的共享知识库
  const sharedKbId = route.query.sharedKbId as string | undefined
  const sharedKbName = route.query.sharedKbName as string | undefined
  const sharedKbPermission = route.query.sharedKbPermission as string | undefined
  if (sharedKbId && sharedKbName) {
    knowledgeStore.setSharedKb({
      id: sharedKbId,
      name: sharedKbName,
      permission: sharedKbPermission || 'query',
    })
    // 清除路由参数，避免刷新页面重复设置
    router.replace({ path: '/' })
    // 自动创建新对话并绑定该共享知识库
    try {
      await chatStore.createNewConversation(undefined, sharedKbId)
    } catch (e) {
      console.error('自动创建对话失败:', e)
    }
  }
})

watch(
  () => [chatStore.messages.length, chatStore.streamingContent],
  () => {
    nextTick(() => {
      if (messagesContainer.value && isUserNearBottom.value) {
        messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
      }
    })
  }
)

async function handleNewConversation() {
  try {
    await chatStore.createNewConversation(undefined, knowledgeStore.selectedBaseId)
  } catch (e: unknown) {
    console.error('新建对话失败:', e)
  }
}

async function handleSelectConversation(conv: Conversation) {
  try {
    await chatStore.selectConversation(conv)
    // 同步知识库选择器：根据对话绑定的知识库更新选择状态
    knowledgeStore.selectBase(conv.knowledge_base_id ?? null)
  } catch (e: unknown) {
    console.error('切换对话失败:', e)
  }
}

async function handleSend() {
  const text = inputText.value.trim()
  if (!text || chatStore.streamingContent) return
  inputText.value = ''
  try {
    await chatStore.sendMessage(text, knowledgeStore.selectedBaseId)
  } catch (e: unknown) {
    console.error('发送消息失败:', e)
  }
}

async function handleRename(conv: Conversation) {
  const newTitle = prompt('输入新标题:', conv.title)
  if (newTitle && newTitle.trim()) {
    try {
      await chatStore.renameConversation(conv.id, newTitle.trim())
    } catch (e: unknown) {
      console.error('重命名失败:', e)
    }
  }
}

async function handleDelete(conv: Conversation) {
  if (confirm(`确定删除对话「${conv.title}」？`)) {
    try {
      await chatStore.deleteConversation(conv.id)
    } catch (e: unknown) {
      console.error('删除对话失败:', e)
    }
  }
}

async function handleExportMarkdown(conv: Conversation) {
  try {
    const response = await exportConversationMarkdown(conv.id)
    const blob = response.data
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${conv.title || '对话'}.md`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  } catch (e: unknown) {
    console.error('导出失败:', e)
    alert('导出失败，请重试')
  }
}

function handleLogout() {
  authStore.logout()
  router.push('/login')
}

function cleanContent(content: string): string {
  if (!content) return ''
  return content.replace(/\[[a-zA-Z_][a-zA-Z0-9_]*\]\s*\n?/g, '').trim()
}

function handleSearchInput() {
  if (searchDebounceTimer) clearTimeout(searchDebounceTimer)
  const q = searchQuery.value.trim()
  if (!q) {
    searchResults.value = []
    searchTotal.value = 0
    return
  }
  searchDebounceTimer = setTimeout(async () => {
    searchLoading.value = true
    try {
      const res = await searchMessages(q)
      searchResults.value = res.data.data.items
      searchTotal.value = res.data.data.total
    } catch (e) {
      console.error('搜索失败:', e)
      searchResults.value = []
      searchTotal.value = 0
    } finally {
      searchLoading.value = false
    }
  }, 300)
}

function clearSearch() {
  searchQuery.value = ''
  searchResults.value = []
  searchTotal.value = 0
}

async function handleSearchResultClick(item: SearchResultItem) {
  const conv = chatStore.conversations.find((c) => c.id === item.conversation_id)
  if (conv) {
    await handleSelectConversation(conv)
  }
  clearSearch()
}

// 监听搜索输入（替代模板中的 @input）
watch(searchQuery, () => {
  handleSearchInput()
})
</script>
