import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Conversation, Message, ToolCall } from '../types'
import {
  createConversation as apiCreate,
  listConversations,
  getConversationDetail,
  deleteConversation as apiDelete,
  renameConversation as apiRename,
  sendMessageStream,
  regenerateMessageStream,
  editAndResendStream,
} from '../api/chat'

export const useChatStore = defineStore('chat', () => {
  const conversations = ref<Conversation[]>([])
  const currentConversation = ref<Conversation | null>(null)
  const messages = ref<Message[]>([])
  const loading = ref(false)
  const streamingContent = ref('')
  const currentToolCalls = ref<ToolCall[]>([])
  const toolRound = ref(0)

  async function loadConversations() {
    try {
      const res = await listConversations()
      conversations.value = res.data.data.items
    } catch (e) {
      console.error('加载对话列表失败:', e)
    }
  }

  async function createNewConversation(title?: string, knowledgeBaseId?: string) {
    const res = await apiCreate(title, knowledgeBaseId)
    const conv = res.data.data
    conversations.value.unshift(conv)
    currentConversation.value = conv
    messages.value = []
    return conv
  }

  async function selectConversation(conv: Conversation) {
    currentConversation.value = conv
    loading.value = true
    try {
      const res = await getConversationDetail(conv.id)
      messages.value = res.data.data.messages
    } finally {
      loading.value = false
    }
  }

  async function deleteConversation(id: string) {
    await apiDelete(id)
    conversations.value = conversations.value.filter((c) => c.id !== id)
    if (currentConversation.value?.id === id) {
      currentConversation.value = null
      messages.value = []
    }
  }

  async function renameConversation(id: string, title: string) {
    await apiRename(id, title)
    const conv = conversations.value.find((c) => c.id === id)
    if (conv) conv.title = title
    if (currentConversation.value?.id === id) {
      currentConversation.value.title = title
    }
  }

  function sendMessage(content: string, knowledgeBaseId?: string | null) {
    if (!currentConversation.value) return
    if (loading.value) return  // 防止重复发送

    loading.value = true

    const userMsg: Message = {
      id: 'temp-' + Date.now(),
      role: 'user',
      content,
      token_count: null,
      latency_ms: null,
      created_at: new Date().toISOString(),
    }
    messages.value.push(userMsg)

    streamingContent.value = ''
    currentToolCalls.value = []
    sendMessageStream(
      currentConversation.value.id,
      content,
      (chunk) => {
        streamingContent.value += chunk
      },
      (fullText) => {
        const assistantMsg: Message = {
          id: 'temp-' + Date.now(),
          role: 'assistant',
          content: fullText || streamingContent.value,
          token_count: null,
          latency_ms: null,
          created_at: new Date().toISOString(),
          tool_calls: currentToolCalls.value.length > 0 ? [...currentToolCalls.value] : undefined,
        }
        messages.value.push(assistantMsg)
        streamingContent.value = ''
        currentToolCalls.value = []
        loading.value = false
        loadConversations()
      },
      (error) => {
        console.error('流式输出错误:', error)
        const errorMsg: Message = {
          id: 'err-' + Date.now(),
          role: 'assistant',
          content: `⚠️ 请求失败: ${error}`,
          token_count: null,
          latency_ms: null,
          created_at: new Date().toISOString(),
        }
        messages.value.push(errorMsg)
        streamingContent.value = ''
        currentToolCalls.value = []
        loading.value = false
      },
      (event: unknown) => {
        const ev = event as { type?: string; round?: number; tool_call_id?: string; name?: string; arguments?: Record<string, unknown>; result?: unknown; status?: string }
        if (ev.type === 'tool_round' && ev.round) {
          toolRound.value = ev.round
          streamingContent.value = ''
          return
        }
        if (!ev.tool_call_id) return
        streamingContent.value = ''
        const existing = currentToolCalls.value.find((t) => t.id === ev.tool_call_id)
        if (existing) {
          if (ev.result !== undefined) existing.result = ev.result
          if (ev.status) existing.status = ev.status as ToolCall['status']
        } else {
          currentToolCalls.value.push({
            id: ev.tool_call_id,
            name: ev.name || 'unknown',
            arguments: ev.arguments || {},
            result: ev.result,
            status: (ev.status as ToolCall['status']) || 'running',
          })
        }
      },
      knowledgeBaseId
    )
  }

  /** 重新生成：删除该 assistant 及之后的消息，用前一条 user 消息重新调 LLM */
  function regenerateMessage(messageId: string) {
    if (!currentConversation.value) return

    const idx = messages.value.findIndex((m) => m.id === messageId)
    if (idx === -1) return

    let prevUserIdx = -1
    for (let i = idx - 1; i >= 0; i--) {
      if (messages.value[i].role === 'user') {
        prevUserIdx = i
        break
      }
    }
    if (prevUserIdx === -1) return

    messages.value = messages.value.slice(0, idx)

    streamingContent.value = ''
    currentToolCalls.value = []

    regenerateMessageStream(
      currentConversation.value.id,
      messageId,
      (chunk) => {
        streamingContent.value += chunk
      },
      (fullText) => {
        const assistantMsg: Message = {
          id: 'temp-' + Date.now(),
          role: 'assistant',
          content: fullText || streamingContent.value,
          token_count: null,
          latency_ms: null,
          created_at: new Date().toISOString(),
          tool_calls: currentToolCalls.value.length > 0 ? [...currentToolCalls.value] : undefined,
        }
        messages.value.push(assistantMsg)
        streamingContent.value = ''
        currentToolCalls.value = []
        loadConversations()
      },
      (error) => {
        console.error('重新生成失败:', error)
        const errorMsg: Message = {
          id: 'err-' + Date.now(),
          role: 'assistant',
          content: `⚠️ 重新生成失败: ${error}`,
          token_count: null,
          latency_ms: null,
          created_at: new Date().toISOString(),
        }
        messages.value.push(errorMsg)
        streamingContent.value = ''
        currentToolCalls.value = []
      },
      (event: unknown) => {
        const ev = event as { type?: string; round?: number; tool_call_id?: string; name?: string; arguments?: Record<string, unknown>; result?: unknown; status?: string }
        if (ev.type === 'tool_round' && ev.round) {
          toolRound.value = ev.round
          return
        }
        if (!ev.tool_call_id) return
        const existing = currentToolCalls.value.find((t) => t.id === ev.tool_call_id)
        if (existing) {
          if (ev.result !== undefined) existing.result = ev.result
          if (ev.status) existing.status = ev.status as ToolCall['status']
        } else {
          currentToolCalls.value.push({
            id: ev.tool_call_id,
            name: ev.name || 'unknown',
            arguments: ev.arguments || {},
            result: ev.result,
            status: (ev.status as ToolCall['status']) || 'running',
          })
        }
      },
    )
  }

  /** 编辑 user 消息并重新发送 */
  function editAndResend(messageId: string, newContent: string) {
    if (!currentConversation.value) return

    const idx = messages.value.findIndex((m) => m.id === messageId)
    if (idx === -1) return

    messages.value[idx].content = newContent
    messages.value = messages.value.slice(0, idx + 1)

    streamingContent.value = ''
    currentToolCalls.value = []

    editAndResendStream(
      currentConversation.value.id,
      messageId,
      newContent,
      (chunk) => {
        streamingContent.value += chunk
      },
      (fullText) => {
        const assistantMsg: Message = {
          id: 'temp-' + Date.now(),
          role: 'assistant',
          content: fullText || streamingContent.value,
          token_count: null,
          latency_ms: null,
          created_at: new Date().toISOString(),
          tool_calls: currentToolCalls.value.length > 0 ? [...currentToolCalls.value] : undefined,
        }
        messages.value.push(assistantMsg)
        streamingContent.value = ''
        currentToolCalls.value = []
        loadConversations()
      },
      (error) => {
        console.error('编辑重发失败:', error)
        const errorMsg: Message = {
          id: 'err-' + Date.now(),
          role: 'assistant',
          content: `⚠️ 编辑重发失败: ${error}`,
          token_count: null,
          latency_ms: null,
          created_at: new Date().toISOString(),
        }
        messages.value.push(errorMsg)
        streamingContent.value = ''
        currentToolCalls.value = []
      },
      (event: unknown) => {
        const ev = event as { type?: string; round?: number; tool_call_id?: string; name?: string; arguments?: Record<string, unknown>; result?: unknown; status?: string }
        if (ev.type === 'tool_round' && ev.round) {
          toolRound.value = ev.round
          return
        }
        if (!ev.tool_call_id) return
        const existing = currentToolCalls.value.find((t) => t.id === ev.tool_call_id)
        if (existing) {
          if (ev.result !== undefined) existing.result = ev.result
          if (ev.status) existing.status = ev.status as ToolCall['status']
        } else {
          currentToolCalls.value.push({
            id: ev.tool_call_id,
            name: ev.name || 'unknown',
            arguments: ev.arguments || {},
            result: ev.result,
            status: (ev.status as ToolCall['status']) || 'running',
          })
        }
      },
    )
  }

  return {
    conversations,
    currentConversation,
    messages,
    loading,
    streamingContent,
    currentToolCalls,
    loadConversations,
    createNewConversation,
    selectConversation,
    deleteConversation,
    renameConversation,
    sendMessage,
    regenerateMessage,
    editAndResend,
  }
})
