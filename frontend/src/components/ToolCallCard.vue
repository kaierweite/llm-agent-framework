<template>
  <div class="flex items-start gap-2 text-xs text-gray-500">
    <span aria-hidden="true">{{ statusIcon }}</span>
    <span class="truncate">{{ summary }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ToolCall } from '../types'

const props = defineProps<{ toolCall: ToolCall }>()

const statusIcon = computed(() => {
  switch (props.toolCall.status) {
    case 'running': return '⏳'
    case 'success': return '✅'
    case 'error': return '❌'
    default: return '⏳'
  }
})

const summary = computed(() => {
  const name = props.toolCall.name || '工具调用'
  const friendlyNames: Record<string, string> = {
    'get_weather': '查询天气',
    'search': '搜索',
    'web_search': '联网搜索',
    'read_file': '读取文件',
    'write_file': '写入文件',
    'execute_code': '执行代码',
    'knowledge_search': '知识库检索',
  }
  const friendly = friendlyNames[name] || name

  if (props.toolCall.status === 'running') return `${friendly}中…`
  if (props.toolCall.status === 'error') return `${friendly}失败`
  return friendly
})
</script>
