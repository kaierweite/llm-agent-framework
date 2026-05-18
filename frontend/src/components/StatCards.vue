<template>
  <div class="grid grid-cols-5 gap-4 mb-6">
    <div
      v-for="stat in cards"
      :key="stat.label"
      class="bg-white rounded-xl border border-gray-200 p-6 flex items-center gap-4"
    >
      <div
        class="w-10 h-10 rounded-lg flex items-center justify-center"
        :class="stat.bgClass"
      >
                <svg
          class="w-5 h-5"
          :class="stat.iconClass"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            :d="stat.icon"
          />
        </svg>
      </div>
      <div>
        <div class="text-2xl font-bold text-gray-900">{{ stat.value }}</div>
        <div class="text-sm text-gray-500">{{ stat.label }}</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { SystemStats } from '../api/admin'

const props = defineProps<{
  stats: SystemStats | null
}>()

const cards = computed(() => [
  {
    label: '总用户数',
    value: props.stats?.total_users ?? '-',
    icon: 'M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z',
    bgClass: 'bg-blue-50',
    iconClass: 'text-blue-600',
  },
  {
    label: '活跃用户',
    value: props.stats?.active_users ?? '-',
    icon: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z',
    bgClass: 'bg-green-50',
    iconClass: 'text-green-600',
  },
  {
    label: '总对话数',
    value: props.stats?.total_conversations ?? '-',
    icon: 'M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z',
    bgClass: 'bg-purple-50',
    iconClass: 'text-purple-600',
  },
  {
    label: '知识库数',
    value: props.stats?.total_knowledge_bases ?? '-',
    icon: 'M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4',
    bgClass: 'bg-orange-50',
    iconClass: 'text-orange-600',
  },
  {
    label: '文档数',
    value: props.stats?.total_documents ?? '-',
    icon: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z',
    bgClass: 'bg-pink-50',
    iconClass: 'text-pink-600',
  },
])
</script>
