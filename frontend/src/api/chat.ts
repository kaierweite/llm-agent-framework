import request from './request'
import type {
  ApiResponse,
  Conversation,
  ConversationDetail,
  PaginatedConversations,
  Message,
  SearchResult,
} from '../types'

// 创建对话
export function createConversation(title?: string, knowledgeBaseId?: string) {
  return request.post<ApiResponse<Conversation>>('/chat/conversations', {
    title: title || '新对话',
    knowledge_base_id: knowledgeBaseId || null,
  })
}

// 对话列表
export function listConversations(page = 1, pageSize = 20) {
  return request.get<ApiResponse<PaginatedConversations>>('/chat/conversations', {
    params: { page, page_size: pageSize },
  })
}

// 对话详情（含历史消息）
export function getConversationDetail(conversationId: string) {
  return request.get<ApiResponse<ConversationDetail>>(`/chat/conversations/${conversationId}`)
}

// 重命名对话
export function renameConversation(conversationId: string, title: string) {
  return request.put<ApiResponse<Conversation>>(`/chat/conversations/${conversationId}`, {
    title,
  })
}

// 删除对话
export function deleteConversation(conversationId: string) {
  return request.delete(`/chat/conversations/${conversationId}`)
}

// 全文搜索消息
export function searchMessages(query: string, limit = 20, offset = 0) {
  return request.get<ApiResponse<SearchResult>>('/chat/search', {
    params: { q: query, limit, offset },
  })
}

// 消息反馈（👍/👎）
export function submitFeedback(conversationId: string, messageId: string, feedback: 'up' | 'down' | null) {
  return request.post<ApiResponse<{ feedback: string | null }>>(
    `/chat/conversations/${conversationId}/messages/${messageId}/feedback`,
    { feedback }
  )
}

// 导出对话为 Markdown
export function exportConversationMarkdown(conversationId: string) {
  return request.get(`/chat/conversations/${conversationId}/export`, {
    params: { format: 'markdown' },
    responseType: 'blob',
  })
}

// 发送消息（同步，非流式）
export function sendMessage(conversationId: string, content: string) {
  return request.post<ApiResponse<{ reply: string }>>(`/chat/conversations/${conversationId}/messages`, {
    content,
  })
}

// ── SSE 流式读取公共逻辑 ──────────────────────────────────
type SSECallbacks = {
  onChunk: (text: string) => void
  onDone: (fullText: string) => void
  onError: (error: string) => void
  onToolCall?: (toolCall: unknown) => void
}

async function _readSSEStream(
  response: Response,
  { onChunk, onDone, onError, onToolCall }: SSECallbacks,
) {
  const reader = response.body?.getReader()
  if (!reader) {
    onError('无法读取响应流')
    return
  }
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const event = JSON.parse(line.slice(6))
          if (event.type === 'chunk') {
            onChunk(event.content)
          } else if (
            (event.type === 'tool_call' || event.type === 'tool_result' || event.type === 'tool_round') &&
            onToolCall
          ) {
            onToolCall(event)
          } else if (event.type === 'done') {
            onDone(event.content)
          } else if (event.type === 'error') {
            onError(event.content)
          }
        } catch {
          // 忽略解析失败的行
        }
      }
    }
  }
}

function _sseFetch(url: string, method: string, body?: unknown, callbacks?: SSECallbacks) {
  const token = localStorage.getItem('token') || ''
  if (!token) {
    callbacks?.onError('未登录，请先登录')
    return
  }

  const init: RequestInit = {
    method,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
  }
  if (body !== undefined) {
    init.body = JSON.stringify(body)
  }

  fetch(url, init)
    .then(async (response) => {
      if (!response.ok) {
        callbacks?.onError(`HTTP ${response.status}`)
        return
      }
      if (callbacks) await _readSSEStream(response, callbacks)
    })
    .catch((err) => {
      callbacks?.onError(err.message || '网络错误')
    })
}

// 发送消息（SSE 流式）
export function sendMessageStream(
  conversationId: string,
  content: string,
  onChunk: (text: string) => void,
  onDone: (fullText: string) => void,
  onError: (error: string) => void,
  onToolCall?: (toolCall: unknown) => void,
  knowledgeBaseId?: string | null,
) {
  _sseFetch(
    `/api/chat/conversations/${conversationId}/messages/stream`,
    'POST',
    { content, knowledge_base_id: knowledgeBaseId || null },
    { onChunk, onDone, onError, onToolCall },
  )
}

// 重新生成 assistant 消息（SSE 流式）
export function regenerateMessageStream(
  conversationId: string,
  messageId: string,
  onChunk: (text: string) => void,
  onDone: (fullText: string) => void,
  onError: (error: string) => void,
  onToolCall?: (toolCall: unknown) => void,
) {
  _sseFetch(
    `/api/chat/conversations/${conversationId}/messages/${messageId}/regenerate`,
    'POST',
    undefined,
    { onChunk, onDone, onError, onToolCall },
  )
}

// 编辑 user 消息并重新生成（SSE 流式）
export function editAndResendStream(
  conversationId: string,
  messageId: string,
  newContent: string,
  onChunk: (text: string) => void,
  onDone: (fullText: string) => void,
  onError: (error: string) => void,
  onToolCall?: (toolCall: unknown) => void,
) {
  _sseFetch(
    `/api/chat/conversations/${conversationId}/messages/${messageId}`,
    'PUT',
    { content: newContent },
    { onChunk, onDone, onError, onToolCall },
  )
}
