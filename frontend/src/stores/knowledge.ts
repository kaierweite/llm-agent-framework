import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { KnowledgeBase, KnowledgeDocument } from '../types'
import { listKnowledgeBases, listDocuments } from '../api/knowledge'

export interface SharedKbInfo {
  id: string
  name: string
  permission: string
}

export const useKnowledgeStore = defineStore('knowledge', () => {
  const bases = ref<KnowledgeBase[]>([])
  const selectedBaseId = ref<string | null>(null)
  const documents = ref<KnowledgeDocument[]>([])
  const loading = ref(false)
  const sharedKb = ref<SharedKbInfo | null>(null)

    async function loadBases() {
    loading.value = true
    try {
      const res = await listKnowledgeBases()
      const items = res.data.data.items
      // 如果有共享知识库且不在自己的列表里，追加到末尾
      if (sharedKb.value && !items.find((b: KnowledgeBase) => b.id === sharedKb.value!.id)) {
        items.push({
          id: sharedKb.value.id,
          name: sharedKb.value.name,
          description: null,
          document_count: 0,
          is_active: true,
          created_at: null,
          updated_at: null,
        } as KnowledgeBase)
      }
      bases.value = items
    } finally {
      loading.value = false
    }
  }

  async function loadDocuments(baseId: string) {
    const res = await listDocuments(baseId)
    documents.value = res.data.data.items
  }

  function selectBase(id: string | null) {
    selectedBaseId.value = id
    if (id) {
      loadDocuments(id)
    } else {
      documents.value = []
    }
  }

  function setSharedKb(info: SharedKbInfo) {
    sharedKb.value = info
    // 如果 bases 列表里还没有这个知识库，添加一个占位条目让选择器能显示
    if (!bases.value.find(b => b.id === info.id)) {
      bases.value.unshift({
        id: info.id,
        name: info.name,
        description: null,
        document_count: 0,
        is_active: true,
        created_at: null,
        updated_at: null,
      } as KnowledgeBase)
    }
    // 自动选中
    selectedBaseId.value = info.id
  }

  function clearSharedKb() {
    sharedKb.value = null
  }

  return {
    bases,
    selectedBaseId,
    documents,
    loading,
    sharedKb,
    loadBases,
    loadDocuments,
    selectBase,
    setSharedKb,
    clearSharedKb,
  }
})
