<template>
  <div class="tool-calls-timeline mt-3 border-t border-gray-700/50 pt-3">
    <button
      @click="expanded = !expanded"
      class="flex items-center gap-2 text-xs text-gray-400 hover:text-gray-300 transition mb-2"
    >
      <svg
        class="w-3.5 h-3.5 transition-transform duration-200"
        :class="{ 'rotate-90': expanded }"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
      </svg>
      <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
      </svg>
      <span>调用了 {{ toolCalls.length }} 个工具</span>
      <span v-if="totalDuration" class="text-gray-500">· {{ totalDuration }}ms</span>
    </button>

    <Transition name="timeline">
      <div v-if="expanded" class="space-y-2 ml-1">
        <div
          v-for="(tc, idx) in toolCalls"
          :key="tc.id || idx"
          class="tool-call-item relative pl-5"
        >
          <!-- 时间线竖线 -->
          <div
            v-if="idx < toolCalls.length - 1"
            class="absolute left-[7px] top-5 w-px h-full bg-gray-700/50"
          />

          <!-- 时间线节点 -->
          <div class="absolute left-0 top-1.5 w-[15px] h-[15px] rounded-full border-2 flex items-center justify-center"
            :class="statusClass(tc.status)"
          >
            <div v-if="tc.status === 'running'" class="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
            <svg v-else-if="tc.status === 'success'" class="w-2 h-2 text-emerald-400" fill="currentColor" viewBox="0 0 8 8">
              <path d="M6.5 1L3 6.5 1.5 5" stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <svg v-else class="w-2 h-2 text-red-400" fill="currentColor" viewBox="0 0 8 8">
              <path d="M1.5 1.5l5 5M6.5 1.5l-5 5" stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round"/>
            </svg>
          </div>

          <!-- 工具卡片 -->
          <div class="rounded-lg border px-3 py-2 text-xs"
            :class="cardClass(tc.status)"
          >
            <div class="flex items-center justify-between gap-2">
              <span class="font-mono font-medium truncate">{{ tc.name }}</span>
              <span class="text-[10px] opacity-60 shrink-0">{{ tc.duration_ms ?? '...' }}ms</span>
            </div>

            <!-- 参数 -->
            <div v-if="tc.arguments && Object.keys(tc.arguments).length > 0" class="mt-1.5">
              <div class="text-[10px] opacity-50 mb-0.5">参数</div>
              <pre class="text-[11px] opacity-70 whitespace-pre-wrap break-all max-h-20 overflow-y-auto">{{ formatArgs(tc.arguments) }}</pre>
            </div>

            <!-- 结果（可展开） -->
            <div v-if="tc.result" class="mt-1.5">
              <button
                @click.stop="toggleResult(idx)"
                class="text-[10px] opacity-50 hover:opacity-80 transition flex items-center gap-1"
              >
                <svg
                  class="w-2.5 h-2.5 transition-transform"
                  :class="{ 'rotate-90': expandedResults.has(idx) }"
                  fill="none" stroke="currentColor" viewBox="0 0 24 24"
                >
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                </svg>
                结果
              </button>
              <div v-if="expandedResults.has(idx)" class="mt-1 text-[11px] opacity-70 whitespace-pre-wrap break-all max-h-32 overflow-y-auto bg-black/20 rounded p-1.5">
                {{ typeof tc.result === 'string' ? tc.result : JSON.stringify(tc.result, null, 2) }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { ToolCall } from '../types'

const props = defineProps<{
  toolCalls: ToolCall[]
}>()

const expanded = ref(false)
const expandedResults = ref(new Set<number>())

const totalDuration = computed(() => {
  return props.toolCalls.reduce((sum, tc) => sum + (tc.duration_ms || 0), 0)
})

function toggleResult(idx: number) {
  const s = new Set(expandedResults.value)
  if (s.has(idx)) s.delete(idx)
  else s.add(idx)
  expandedResults.value = s
}

function formatArgs(args: Record<string, unknown>): string {
  try {
    return JSON.stringify(args, null, 2)
  } catch {
    return String(args)
  }
}

function statusClass(status: string) {
  switch (status) {
    case 'running': return 'border-blue-500/50 bg-blue-500/10'
    case 'success': return 'border-emerald-500/50 bg-emerald-500/10'
    case 'error': return 'border-red-500/50 bg-red-500/10'
    default: return 'border-gray-500/50 bg-gray-500/10'
  }
}

function cardClass(status: string) {
  switch (status) {
    case 'running': return 'border-blue-500/20 bg-blue-500/5'
    case 'success': return 'border-emerald-500/20 bg-emerald-500/5'
    case 'error': return 'border-red-500/20 bg-red-500/5'
    default: return 'border-gray-500/20 bg-gray-500/5'
  }
}
</script>

<style scoped>
.timeline-enter-active,
.timeline-leave-active {
  transition: all 0.2s ease;
}
.timeline-enter-from,
.timeline-leave-to {
  opacity: 0;
  max-height: 0;
  overflow: hidden;
}
.timeline-enter-to,
.timeline-leave-from {
  opacity: 1;
  max-height: 2000px;
}
</style>
