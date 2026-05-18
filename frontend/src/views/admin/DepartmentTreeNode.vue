<template>
  <div>
    <div
      class="flex items-center gap-1 px-3 py-1.5 cursor-pointer group text-sm transition-colors rounded-md mx-1"
      :class="selectedId === node.id ? 'bg-blue-50 text-blue-700 font-medium' : 'text-gray-700 hover:bg-gray-50'"
      :style="{ paddingLeft: `${depth * 16 + 12}px` }"
      @click="$emit('select', node.id)"
    >
      <!-- 展开/收起箭头 -->
      <button
        v-if="hasChildren"
        @click.stop="expanded = !expanded"
        class="w-4 h-4 flex items-center justify-center text-gray-400 hover:text-gray-600 shrink-0"
      >
        <svg class="w-3 h-3 transition-transform" :class="expanded ? 'rotate-90' : ''" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
        </svg>
      </button>
      <span v-else class="w-4 shrink-0"></span>

      <!-- 部门图标 -->
      <svg class="w-4 h-4 shrink-0" :class="selectedId === node.id ? 'text-blue-600' : 'text-gray-400'" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
      </svg>

      <!-- 部门名称 -->
      <span class="flex-1 truncate">{{ node.name }}</span>

      <!-- 成员数 badge -->
      <span class="text-xs text-gray-400 tabular-nums">{{ node.member_count }}</span>

      <!-- 操作按钮（hover 显示） -->
      <div class="hidden group-hover:flex items-center gap-0.5 shrink-0" @click.stop>
        <button @click="$emit('create-child', node)" class="w-5 h-5 flex items-center justify-center text-gray-400 hover:text-blue-600 rounded" title="添加子部门">
          <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" /></svg>
        </button>
        <button @click="$emit('edit', node)" class="w-5 h-5 flex items-center justify-center text-gray-400 hover:text-gray-700 rounded" title="编辑">
          <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" /></svg>
        </button>
        <button @click="$emit('delete', node)" class="w-5 h-5 flex items-center justify-center text-gray-400 hover:text-red-600 rounded" title="删除">
          <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
        </button>
      </div>
    </div>

    <!-- 子节点 -->
    <div v-if="expanded && hasChildren">
      <DepartmentTreeNode
        v-for="child in node.children"
        :key="child.id"
        :node="child"
        :selected-id="selectedId"
        :depth="depth + 1"
        @select="(id) => $emit('select', id)"
        @create-child="(dept) => $emit('create-child', dept)"
        @edit="(dept) => $emit('edit', dept)"
        @delete="(dept) => $emit('delete', dept)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { Department } from '../../api/department'

const props = defineProps<{
  node: Department
  selectedId: string | null
  depth: number
}>()

defineEmits<{
  select: [id: string]
  'create-child': [dept: Department]
  edit: [dept: Department]
  delete: [dept: Department]
}>()

const expanded = ref(props.depth < 1)
const hasChildren = computed(() => (props.node.children?.length ?? 0) > 0)
</script>
