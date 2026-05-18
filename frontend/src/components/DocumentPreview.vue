<template>
  <div class="document-preview">
    <!-- 加载中 -->
    <div v-if="loading" class="preview-loading">
      <div class="spinner"></div>
      <p class="text-gray-500 mt-2">加载预览中...</p>
    </div>

    <!-- 错误 -->
    <div v-else-if="error" class="preview-error">
      <div class="text-4xl text-gray-300">⚠</div>
      <p class="text-gray-500 mt-2">{{ error }}</p>
    </div>

    <!-- 不支持 -->
    <div v-else-if="previewData?.type === 'unsupported'" class="preview-unsupported">
      <div class="text-4xl text-gray-300">📄</div>
      <p class="text-gray-500 mt-2">{{ previewData.message || '该文件格式暂不支持预览' }}</p>
    </div>

    <!-- Markdown 渲染 -->
    <div
      v-else-if="previewData?.type === 'markdown'"
      class="preview-markdown markdown-body"
      v-html="renderedMarkdown"
    />

    <!-- 代码高亮 -->
    <div v-else-if="previewData?.type === 'code'" class="preview-code">
      <div class="code-lang-tag">{{ previewData.language }}</div>
      <pre><code>{{ previewData.content }}</code></pre>
    </div>

    <!-- 表格 -->
    <div v-else-if="previewData?.type === 'table'" class="preview-table">
      <!-- 多 sheet 用 tab 切换 -->
      <div v-if="previewData.sheets?.length > 1" class="sheet-tabs">
        <button
          v-for="(sheet, idx) in previewData.sheets"
          :key="idx"
          :class="['sheet-tab', { active: activeSheet === String(idx) }]"
          @click="activeSheet = String(idx)"
        >
          {{ sheet.name }}
        </button>
      </div>
      <div v-if="currentSheet" class="table-scroll">
        <table>
          <thead>
            <tr>
              <th v-for="(h, i) in currentSheet.headers" :key="i">{{ h }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, ri) in currentSheet.rows" :key="ri">
              <td v-for="(cell, ci) in row" :key="ci">{{ cell }}</td>
            </tr>
          </tbody>
        </table>
        <div v-if="currentSheet.rows?.length >= 200" class="text-xs text-gray-400 text-center py-2">
          仅显示前 200 行
        </div>
      </div>
    </div>

    <!-- 幻灯片 -->
    <div v-else-if="previewData?.type === 'slides'" class="preview-slides">
      <div class="slides-nav">
        <button class="nav-btn" :disabled="currentSlide <= 0" @click="currentSlide--">‹</button>
        <span class="text-sm text-gray-600">{{ currentSlide + 1 }} / {{ previewData.slides.length }}</span>
        <button class="nav-btn" :disabled="currentSlide >= previewData.slides.length - 1" @click="currentSlide++">›</button>
      </div>
      <div class="slide-card">
        <div class="slide-page-num">第 {{ previewData.slides[currentSlide].page }} 页</div>
        <ul>
          <li v-for="(text, ti) in previewData.slides[currentSlide].texts" :key="ti">{{ text }}</li>
        </ul>
      </div>
    </div>

    <!-- DOCX 段落 -->
    <div v-else-if="previewData?.type === 'docx'" class="preview-docx">
      <template v-for="(p, pi) in previewData.paragraphs" :key="pi">
        <h1 v-if="p.level === 1" class="docx-h1">{{ p.text }}</h1>
        <h2 v-else-if="p.level === 2" class="docx-h2">{{ p.text }}</h2>
        <h3 v-else-if="p.level === 3" class="docx-h3">{{ p.text }}</h3>
        <p v-else class="docx-p">{{ p.text }}</p>
      </template>
    </div>

    <!-- PDF iframe -->
    <div v-else-if="previewData?.type === 'pdf'" class="preview-pdf">
      <iframe :src="pdfUrl" />
    </div>

    <!-- 纯文本 -->
    <div v-else-if="previewData?.type === 'text'" class="preview-text">
      <pre>{{ previewData.content }}</pre>
    </div>

    <!-- 未知类型 fallback -->
    <div v-else class="preview-unsupported">
      <div class="text-4xl text-gray-300">📄</div>
      <p class="text-gray-500 mt-2">无法预览此文件类型</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useAuthStore } from '../stores/auth'

interface PreviewData {
  type: string
  content?: string
  raw?: string
  language?: string
  file_url?: string
  message?: string
  sheets?: Array<{
    name: string
    headers: string[]
    rows: string[][]
  }>
  slides?: Array<{
    page: number
    texts: string[]
  }>
  paragraphs?: Array<{
    text: string
    level: number
  }>
}

const props = defineProps<{
  previewData: PreviewData | null
  loading?: boolean
  error?: string
}>()

const authStore = useAuthStore()
const activeSheet = ref('0')
const currentSlide = ref(0)

// 当前显示的 sheet
const currentSheet = computed(() => {
  if (!props.previewData?.sheets) return null
  const idx = parseInt(activeSheet.value) || 0
  return props.previewData.sheets[idx] || null
})

// 重置状态当数据变化
watch(() => props.previewData, () => {
  activeSheet.value = '0'
  currentSlide.value = 0
})

// Markdown 渲染（后端已返回 HTML）
const renderedMarkdown = computed(() => {
  if (!props.previewData || props.previewData.type !== 'markdown') return ''
  return props.previewData.content || ''
})

// PDF URL 带 token
const pdfUrl = computed(() => {
  if (!props.previewData || props.previewData.type !== 'pdf') return ''
  const baseUrl = props.previewData.file_url || ''
  const separator = baseUrl.includes('?') ? '&' : '?'
  return `${baseUrl}${separator}token=${authStore.token}`
})
</script>

<style scoped>
.document-preview {
  height: 100%;
  overflow: auto;
}

/* 加载中 */
.preview-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
}
.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #e5e7eb;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 错误/不支持 */
.preview-error,
.preview-unsupported {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
}

/* Markdown */
.preview-markdown {
  padding: 16px;
  line-height: 1.7;
  color: #303133;
}
.preview-markdown :deep(h1) { font-size: 1.5em; font-weight: 700; margin: 16px 0 8px; }
.preview-markdown :deep(h2) { font-size: 1.3em; font-weight: 600; margin: 14px 0 6px; }
.preview-markdown :deep(h3) { font-size: 1.1em; font-weight: 600; margin: 12px 0 4px; }
.preview-markdown :deep(p) { margin: 8px 0; }
.preview-markdown :deep(ul),
.preview-markdown :deep(ol) { padding-left: 24px; margin: 8px 0; }
.preview-markdown :deep(code) {
  background: #f3f4f6;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.9em;
  font-family: 'Fira Code', 'Consolas', monospace;
}
.preview-markdown :deep(pre) {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 16px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 12px 0;
}
.preview-markdown :deep(pre code) {
  background: none;
  padding: 0;
  color: inherit;
}
.preview-markdown :deep(blockquote) {
  border-left: 4px solid #3b82f6;
  padding-left: 12px;
  color: #6b7280;
  margin: 8px 0;
}
.preview-markdown :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 12px 0;
}
.preview-markdown :deep(th),
.preview-markdown :deep(td) {
  border: 1px solid #e5e7eb;
  padding: 8px 12px;
  text-align: left;
}
.preview-markdown :deep(th) {
  background: #f9fafb;
  font-weight: 600;
}

/* 代码 */
.preview-code {
  position: relative;
  padding: 16px;
}
.code-lang-tag {
  position: absolute;
  top: 8px;
  right: 12px;
  font-size: 11px;
  color: #9ca3af;
  text-transform: uppercase;
}
.preview-code pre {
  margin: 0;
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 16px;
  border-radius: 8px;
  overflow-x: auto;
  font-size: 13px;
  line-height: 1.6;
  font-family: 'Fira Code', 'Consolas', monospace;
}

/* 表格 */
.sheet-tabs {
  display: flex;
  gap: 4px;
  padding: 8px 16px 0;
  border-bottom: 1px solid #e5e7eb;
}
.sheet-tab {
  padding: 6px 16px;
  font-size: 13px;
  border: 1px solid #e5e7eb;
  border-bottom: none;
  border-radius: 6px 6px 0 0;
  background: #f9fafb;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.2s;
}
.sheet-tab.active {
  background: #fff;
  color: #303133;
  border-color: #3b82f6;
  border-bottom: 1px solid #fff;
  margin-bottom: -1px;
}
.table-scroll {
  overflow-x: auto;
  padding: 0 16px 16px;
}
.table-scroll table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.table-scroll th,
.table-scroll td {
  border: 1px solid #e5e7eb;
  padding: 6px 10px;
  text-align: left;
  white-space: nowrap;
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
}
.table-scroll th {
  background: #f9fafb;
  font-weight: 600;
  position: sticky;
  top: 0;
}

/* 幻灯片 */
.preview-slides {
  padding: 16px;
}
.slides-nav {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  margin-bottom: 16px;
}
.nav-btn {
  width: 32px;
  height: 32px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: #fff;
  color: #374151;
  font-size: 18px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}
.nav-btn:hover:not(:disabled) {
  background: #f3f4f6;
  border-color: #3b82f6;
  color: #3b82f6;
}
.nav-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.slide-card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 24px;
  min-height: 200px;
}
.slide-page-num {
  font-size: 12px;
  color: #9ca3af;
  margin-bottom: 12px;
}
.slide-card ul {
  list-style: none;
  padding: 0;
  margin: 0;
}
.slide-card li {
  padding: 6px 0;
  font-size: 14px;
  color: #374151;
  border-bottom: 1px solid #f3f4f6;
}
.slide-card li:last-child {
  border-bottom: none;
}

/* DOCX */
.preview-docx {
  padding: 16px;
}
.docx-h1 { font-size: 1.5em; font-weight: 700; margin: 16px 0 8px; color: #111827; }
.docx-h2 { font-size: 1.3em; font-weight: 600; margin: 14px 0 6px; color: #1f2937; }
.docx-h3 { font-size: 1.1em; font-weight: 600; margin: 12px 0 4px; color: #374151; }
.docx-p {
  font-size: 14px;
  line-height: 1.7;
  color: #4b5563;
  margin: 6px 0;
}

/* PDF */
.preview-pdf {
  width: 100%;
  height: 100%;
}
.preview-pdf iframe {
  width: 100%;
  height: 100%;
  min-height: 500px;
  border: none;
  border-radius: 8px;
}
.document-preview:has(.preview-pdf) {
  display: flex;
  flex-direction: column;
}

/* 纯文本 */
.preview-text {
  padding: 16px;
}
.preview-text pre {
  margin: 0;
  white-space: pre-wrap;
  word-wrap: break-word;
  font-size: 13px;
  line-height: 1.6;
  color: #303133;
  font-family: 'Fira Code', 'Consolas', monospace;
  background: #f5f7fa;
  padding: 16px;
  border-radius: 8px;
}
</style>
