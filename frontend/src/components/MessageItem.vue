<template>
  <div class="flex flex-col gap-2 group/msg" :class="msg.role === 'user' ? 'items-end' : 'items-start'">
    <!-- user 消息 -->
    <div v-if="msg.role === 'user'" class="max-w-[70%] relative">
      <!-- 编辑模式 -->
      <div v-if="isEditing" class="flex flex-col gap-2">
        <textarea
          ref="editInputRef"
          v-model="editContent"
          rows="3"
          class="w-full px-4 py-3 rounded-2xl text-sm leading-relaxed bg-white text-gray-800 border border-blue-400 focus:ring-2 focus:ring-blue-500 outline-none resize-none"
          @keydown.escape="$emit('cancel-edit')"
          @keydown.ctrl.enter="submitEdit"
          @keydown.meta.enter="submitEdit"
        />
        <div class="flex gap-2 justify-end">
          <button
            @click="$emit('cancel-edit')"
            class="px-3 py-1 text-xs rounded-lg border border-gray-300 text-gray-600 hover:bg-gray-100 transition"
          >取消</button>
          <button
            @click="submitEdit"
            :disabled="!editContent.trim()"
            class="px-3 py-1 text-xs rounded-lg bg-blue-600 text-white hover:bg-blue-700 transition disabled:opacity-50"
          >保存并重新生成</button>
        </div>
        <p class="text-[10px] text-gray-400 text-right">Esc 取消 · Ctrl+Enter 保存</p>
      </div>
      <!-- 显示模式 -->
      <div v-else class="relative group">
        <div class="px-4 py-3 rounded-2xl rounded-br-md bg-blue-600 text-white text-sm leading-relaxed whitespace-pre-wrap">{{ msg.content }}</div>
        <button
          @click="$emit('start-edit', msg)"
          class="absolute -left-8 top-1/2 -translate-y-1/2 opacity-0 group-hover/msg:opacity-100 p-1 rounded hover:bg-blue-100 transition text-blue-500"
          title="编辑消息"
          aria-label="编辑消息"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" /></svg>
        </button>
      </div>
    </div>

    <!-- assistant 消息 -->
    <div v-if="msg.role === 'assistant'" class="max-w-[70%] relative group">
      <div class="px-4 py-3 rounded-2xl rounded-bl-md bg-white text-gray-800 border border-gray-200 shadow-sm text-sm leading-relaxed whitespace-pre-wrap">{{ cleanedContent }}</div>
      <!-- 反馈按钮 -->
      <div v-if="showActions" class="flex items-center gap-1 mt-1 opacity-0 group-hover/msg:opacity-100 transition">
        <button
          @click="$emit('feedback', msg, 'up')"
          :disabled="feedbackSubmitting"
          class="p-1 rounded transition"
          :class="msg.feedback === 'up' ? 'text-green-600 bg-green-50' : 'text-gray-400 hover:text-green-600 hover:bg-green-50'"
          title="有帮助"
          aria-label="有帮助"
        >
          <svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24"><path d="M2 20h2V8H2v12zm20-11a2 2 0 00-2-2h-6.31l.95-4.57.03-.32a1.49 1.49 0 00-.44-1.06L13.17 0 6.59 6.59C6.22 6.95 6 7.45 6 8v10a2 2 0 002 2h9c.83 0 1.54-.5 1.84-1.22l3.02-7.05c.09-.23.14-.47.14-.73v-2z"/></svg>
        </button>
        <button
          @click="$emit('feedback', msg, 'down')"
          :disabled="feedbackSubmitting"
          class="p-1 rounded transition"
          :class="msg.feedback === 'down' ? 'text-red-600 bg-red-50' : 'text-gray-400 hover:text-red-600 hover:bg-red-50'"
          title="没帮助"
          aria-label="没帮助"
        >
          <svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24"><path d="M22 4h-2v12h2V4zM2.09 11.97A1.99 1.99 0 004 14h6.31l-.95 4.57-.03.32c0 .42.17.8.44 1.06L10.83 24l6.59-6.59c.36-.36.58-.86.58-1.41V6a2 2 0 00-2-2H6.91c-.83 0-1.54.5-1.84 1.22l-3.02 7.05c-.09.23-.14.47-.14.73v2z"/></svg>
        </button>
      </div>
      <!-- 重新生成按钮 -->
      <button
        v-if="showActions"
        @click="$emit('regenerate', msg.id)"
        :disabled="isStreaming"
        class="absolute -right-8 top-1/2 -translate-y-1/2 opacity-0 group-hover/msg:opacity-100 p-1 rounded hover:bg-gray-100 transition text-gray-400 hover:text-gray-600 disabled:opacity-30"
        title="重新生成"
        aria-label="重新生成回复"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import type { Message } from '../types'

const props = defineProps<{
  msg: Message
  isEditing: boolean
  editingContent: string
  feedbackSubmitting: boolean
  isStreaming: boolean
}>()

const emit = defineEmits<{
  'start-edit': [msg: Message]
  'cancel-edit': []
  'confirm-edit': [messageId: string, content: string]
  'feedback': [msg: Message, type: 'up' | 'down']
  'regenerate': [messageId: string]
}>()

const editInputRef = ref<HTMLTextAreaElement | null>(null)
const editContent = ref(props.editingContent)

// 同步父组件的 editingContent
watch(() => props.editingContent, (val) => { editContent.value = val })
// 编辑模式激活时聚焦
watch(() => props.isEditing, (val) => {
  if (val) {
    nextTick(() => {
      const el = Array.isArray(editInputRef.value) ? editInputRef.value[0] : editInputRef.value
      el?.focus()
      el?.select()
    })
  }
})

const showActions = computed(() => !props.msg.id.startsWith('temp-') && !props.msg.id.startsWith('err-'))

const cleanedContent = computed(() => {
  if (!props.msg.content) return ''
  return props.msg.content.replace(/\[[a-zA-Z_][a-zA-Z0-9_]*\]\s*\n?/g, '').trim()
})

function submitEdit() {
  const content = editContent.value.trim()
  if (!content) return
  emit('confirm-edit', props.msg.id, content)
}
</script>
