<template>
  <div class="relative">
        <button
      @click="showDropdown = !showDropdown"
      :aria-expanded="showDropdown"
      aria-haspopup="listbox"
      class="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-600 bg-gray-100 hover:bg-gray-200 rounded-lg transition"
    >
      <svg class="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
      </svg>
      <span class="truncate max-w-[160px]">{{ selectedLabel }}</span>
      <svg class="w-3.5 h-3.5 text-gray-400 transition-transform" :class="{ 'rotate-180': showDropdown }" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
      </svg>
    </button>

        <div
      v-if="showDropdown"
      role="listbox"
      aria-label="选择知识库"
      class="absolute bottom-full mb-1 left-0 w-64 bg-white border border-gray-200 rounded-xl shadow-lg z-50 overflow-hidden"
    >
      <div class="px-3 py-2 border-b border-gray-100">
        <p class="text-xs text-gray-400">选择知识库</p>
      </div>
      <div class="max-h-60 overflow-y-auto py-1">
                <button
          @click="handleSelect(null)"
          role="option"
          :aria-selected="knowledgeStore.selectedBaseId === null"
          class="w-full text-left px-3 py-2 text-sm hover:bg-gray-50 transition"
          :class="knowledgeStore.selectedBaseId === null ? 'text-blue-600 bg-blue-50' : 'text-gray-700'"
        >
          <span class="flex items-center gap-2">
                        <svg class="w-4 h-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
            无知识库（纯对话）
          </span>
        </button>
                <button
          v-for="base in knowledgeStore.bases"
          :key="base.id"
          @click="handleSelect(base.id)"
          role="option"
          :aria-selected="knowledgeStore.selectedBaseId === base.id"
          class="w-full text-left px-3 py-2 text-sm hover:bg-gray-50 transition"
          :class="knowledgeStore.selectedBaseId === base.id ? 'text-blue-600 bg-blue-50' : 'text-gray-700'"
        >
          <span class="flex items-center gap-2">
                        <svg v-if="base.is_shared" class="w-4 h-4 text-amber-500 opacity-80" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
            </svg>
            <svg v-else class="w-4 h-4 text-blue-500 opacity-60" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
            </svg>
            <span class="truncate flex-1">{{ base.name }}</span>
            <span v-if="base.is_shared" class="text-xs text-amber-500 shrink-0">共享</span>
            <span v-else class="text-xs text-gray-400 shrink-0">{{ base.document_count }} 文档</span>
          </span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useKnowledgeStore } from '../stores/knowledge'

const knowledgeStore = useKnowledgeStore()
const showDropdown = ref(false)

const selectedLabel = computed(() => {
  if (!knowledgeStore.selectedBaseId) return '无知识库'
  const base = knowledgeStore.bases.find((b) => b.id === knowledgeStore.selectedBaseId)
  return base?.name || '无知识库'
})

function handleSelect(id: string | null) {
  knowledgeStore.selectBase(id)
  showDropdown.value = false
}

function handleClickOutside(e: MouseEvent) {
  const target = e.target as HTMLElement
  if (!target.closest('.relative')) {
    showDropdown.value = false
  }
}

onMounted(() => {
  knowledgeStore.loadBases()
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>
