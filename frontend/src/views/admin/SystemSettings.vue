<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h2 class="text-xl font-semibold text-gray-800">系统设置</h2>
    </div>

    <StatCards :stats="stats" />

    <div class="bg-white rounded-xl border border-gray-200 p-6 mb-6">
      <div class="flex items-center justify-between mb-4">
        <h3 class="text-base font-semibold text-gray-800">健康检查</h3>
        <button
          class="px-3 py-1.5 rounded-lg text-xs font-medium bg-gray-100 text-gray-600 hover:bg-gray-200 transition-colors"
          :disabled="healthLoading"
          @click="fetchHealth"
        >
          {{ healthLoading ? '检查中...' : '刷新' }}
        </button>
      </div>
      <div v-if="healthLoading && !health" class="p-6 text-center">
        <div class="inline-block w-6 h-6 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
      </div>
      <div v-else-if="health" class="grid grid-cols-3 gap-4">
        <div
          v-for="(item, key) in health"
          :key="key"
          class="flex items-center gap-3 p-3 rounded-lg border"
          :class="item.status === 'ok' ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'"
        >
          <div class="w-3 h-3 rounded-full" :class="item.status === 'ok' ? 'bg-green-500' : 'bg-red-500'"></div>
          <div class="flex-1">
            <p class="text-sm font-medium text-gray-800">{{ healthLabels[key as string] || key }}</p>
            <p class="text-xs text-gray-500">{{ item.status === 'ok' ? `${item.latency_ms}ms` : '异常' }}</p>
          </div>
        </div>
      </div>
    </div>

    <div class="bg-white rounded-xl border border-gray-200 p-6 mb-6">
      <h3 class="text-base font-semibold text-gray-800 mb-4">LLM 服务配置</h3>

      <div v-if="configLoading" class="p-8 text-center">
        <div class="inline-block w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
        <p class="text-gray-400 mt-4">加载中...</p>
      </div>

      <div v-else class="space-y-4">
        <div class="flex items-center gap-4">
          <label class="w-36 shrink-0 text-sm font-medium text-gray-700 text-right">API 地址</label>
          <input
            v-model="configForm.llm_base_url"
            type="text"
            placeholder="http://localhost:11434/v1"
            class="flex-1 px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
          />
        </div>
        <div class="flex items-center gap-4">
          <label class="w-36 shrink-0 text-sm font-medium text-gray-700 text-right">模型名称</label>
          <input
            v-model="configForm.llm_model"
            type="text"
            placeholder="gpt-4o-mini"
            class="flex-1 px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
          />
        </div>
        <div class="flex items-center gap-4">
          <label class="w-36 shrink-0 text-sm font-medium text-gray-700 text-right">API Key</label>
          <div class="relative flex-1">
            <input
              v-model="configForm.llm_api_key"
              :type="showLLMKey ? 'text' : 'password'"
              placeholder="留空表示不修改"
              class="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 pr-10"
            />
                        <button class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600" @click="showLLMKey = !showLLMKey" :aria-label="showLLMKey ? '隐藏密钥' : '显示密钥'">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" /></svg>
            </button>
          </div>
                              <span v-if="config.llm_api_key" class="text-xs text-gray-400">当前：{{ maskKey(config.llm_api_key) }}</span>
        </div>
        <div class="flex items-center gap-4 pt-2">
          <div class="w-36 shrink-0"></div>
          <button
            class="px-4 py-2 rounded-lg text-sm font-medium border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors disabled:opacity-50"
            :disabled="llmTesting"
            @click="handleTestLLM"
          >
            {{ llmTesting ? '测试中...' : '测试连接' }}
          </button>
          <span v-if="llmTestResult" class="text-sm" :class="llmTestResult.status === 'ok' ? 'text-green-600' : 'text-red-600'">
            {{ llmTestResult.message }}
          </span>
        </div>
      </div>
    </div>

    <div class="bg-white rounded-xl border border-gray-200 p-6 mb-6">
      <h3 class="text-base font-semibold text-gray-800 mb-4">AnythingLLM 配置</h3>

      <div v-if="configLoading" class="p-8 text-center">
        <div class="inline-block w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
      </div>

      <div v-else class="space-y-4">
        <div class="flex items-center gap-4">
          <label class="w-36 shrink-0 text-sm font-medium text-gray-700 text-right">服务地址</label>
          <input
            v-model="configForm.anythingllm_base_url"
            type="text"
            placeholder="http://localhost:3001"
            class="flex-1 px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
          />
        </div>
        <div class="flex items-center gap-4">
          <label class="w-36 shrink-0 text-sm font-medium text-gray-700 text-right">API Key</label>
          <div class="relative flex-1">
            <input
              v-model="configForm.anythingllm_api_key"
              :type="showAllmKey ? 'text' : 'password'"
              placeholder="留空表示不修改"
              class="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 pr-10"
            />
                        <button class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600" @click="showAllmKey = !showAllmKey" :aria-label="showAllmKey ? '隐藏密钥' : '显示密钥'">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" /></svg>
            </button>
          </div>
                    <span v-if="config.anythingllm_api_key" class="text-xs text-gray-400">当前：{{ maskKey(config.anythingllm_api_key) }}</span>
        </div>
        <div class="flex items-center gap-4 pt-2">
          <div class="w-36 shrink-0"></div>
          <button
            class="px-4 py-2 rounded-lg text-sm font-medium border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors disabled:opacity-50"
            :disabled="allmTesting"
            @click="handleTestAnythingLLM"
          >
            {{ allmTesting ? '测试中...' : '测试连接' }}
          </button>
          <span v-if="allmTestResult" class="text-sm" :class="allmTestResult.status === 'ok' ? 'text-green-600' : 'text-red-600'">
            {{ allmTestResult.message }}
          </span>
        </div>
      </div>
    </div>

    <div class="flex items-center gap-3 mb-6">
      <button
        class="px-5 py-2 rounded-lg text-sm font-medium bg-blue-600 text-white hover:bg-blue-700 transition-colors disabled:opacity-50"
        :disabled="saving"
        @click="handleSaveConfig"
      >
        {{ saving ? '保存中...' : '保存配置' }}
      </button>
      <span v-if="saveMessage" class="text-sm" :class="saveSuccess ? 'text-green-600' : 'text-red-600'">
        {{ saveMessage }}
      </span>
    </div>

    <div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div
        class="flex items-center justify-between px-6 py-4 cursor-pointer hover:bg-gray-50 transition-colors"
        @click="showSkills = !showSkills"
      >
        <h3 class="text-base font-semibold text-gray-800">技能管理</h3>
                <svg
          class="w-5 h-5 text-gray-400 transition-transform"
          :class="{ 'rotate-180': showSkills }"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
        </svg>
      </div>

      <div v-if="showSkills" class="border-t border-gray-200">
        <div class="px-6 py-4 flex justify-end">
          <button
            class="px-4 py-2 rounded-lg text-sm font-medium bg-blue-600 text-white hover:bg-blue-700 transition-colors"
            @click="showSkillDialog = true"
          >
            添加技能
          </button>
        </div>

        <div v-if="skillsLoading" class="px-6 pb-8 text-center">
          <div class="inline-block w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
        </div>

        <div v-else-if="skills.length === 0" class="px-6 pb-8 text-center">
          <p class="text-gray-400">暂无技能</p>
        </div>

        <table v-else class="w-full">
          <thead class="bg-gray-50">
            <tr>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">名称</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">显示名</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">版本</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">作者</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">状态</th>
              <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">操作</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-200">
            <tr v-for="skill in skills" :key="skill.id" class="hover:bg-gray-50 transition-colors">
              <td class="px-6 py-4 text-sm text-gray-900 font-mono">{{ skill.name }}</td>
              <td class="px-6 py-4 text-sm text-gray-600">{{ skill.display_name }}</td>
              <td class="px-6 py-4 text-sm text-gray-500">{{ skill.version }}</td>
              <td class="px-6 py-4 text-sm text-gray-500">{{ skill.author || '-' }}</td>
              <td class="px-6 py-4">
                <span
                  class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
                  :class="skill.is_enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'"
                >
                  {{ skill.is_enabled ? '启用' : '禁用' }}
                </span>
              </td>
              <td class="px-6 py-4 text-right">
                <div class="flex items-center justify-end gap-2">
                  <button
                    class="px-3 py-1.5 rounded-lg text-xs font-medium transition-colors"
                    :class="skill.is_enabled ? 'bg-yellow-50 text-yellow-600 hover:bg-yellow-100' : 'bg-green-50 text-green-600 hover:bg-green-100'"
                    @click="handleToggleSkill(skill)"
                  >
                    {{ skill.is_enabled ? '禁用' : '启用' }}
                  </button>
                  <button
                    class="px-3 py-1.5 rounded-lg text-xs font-medium bg-red-50 text-red-600 hover:bg-red-100 transition-colors"
                    @click="handleDeleteSkill(skill)"
                  >
                    删除
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="showSkillDialog" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40" @click.self="showSkillDialog = false">
      <div class="bg-white rounded-xl p-6 w-full max-w-md shadow-xl">
        <h3 class="text-lg font-semibold text-gray-900 mb-4">添加技能</h3>
        <div class="space-y-3">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">标识名 <span class="text-red-500">*</span></label>
            <input
              v-model="skillForm.name"
              type="text"
              placeholder="如 web_search"
              class="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">显示名 <span class="text-red-500">*</span></label>
            <input
              v-model="skillForm.display_name"
              type="text"
              placeholder="如 网页搜索"
              class="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">描述</label>
            <input
              v-model="skillForm.description"
              type="text"
              placeholder="可选"
              class="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">版本</label>
            <input
              v-model="skillForm.version"
              type="text"
              placeholder="1.0.0"
              class="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">作者</label>
            <input
              v-model="skillForm.author"
              type="text"
              placeholder="可选"
              class="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
            />
          </div>
        </div>
        <div class="flex justify-end gap-3 mt-6">
          <button
            class="px-4 py-2 rounded-lg text-sm font-medium border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors"
            @click="showSkillDialog = false"
          >
            取消
          </button>
          <button
            class="px-4 py-2 rounded-lg text-sm font-medium bg-blue-600 text-white hover:bg-blue-700 transition-colors disabled:opacity-50"
            :disabled="!skillForm.name.trim() || !skillForm.display_name.trim()"
            @click="handleCreateSkill"
          >
            创建
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import StatCards from '../../components/StatCards.vue'
import {
  getStats,
  getSkills,
  createSkill,
  toggleSkillEnabled,
  deleteSkill,
  getSystemConfig,
  updateSystemConfig,
  testLLMConnection,
  testAnythingLLMConnection,
  getHealthCheck,
} from '../../api/admin'
import type { SystemStats, AdminSkill, SystemConfig } from '../../api/admin'

const stats = ref<SystemStats | null>(null)

const configLoading = ref(true)
const config = ref<SystemConfig>({
  llm_base_url: '',
  llm_model: '',
  llm_api_key: '',
  anythingllm_base_url: '',
  anythingllm_api_key: '',
  cors_origins: '',
})
const configForm = reactive({
  llm_base_url: '',
  llm_model: '',
  llm_api_key: '',
  anythingllm_base_url: '',
  anythingllm_api_key: '',
})
const showLLMKey = ref(false)
const showAllmKey = ref(false)

const saving = ref(false)
const saveMessage = ref('')
const saveSuccess = ref(false)

const llmTesting = ref(false)
const llmTestResult = ref<{ status: string; message: string } | null>(null)
const allmTesting = ref(false)
const allmTestResult = ref<{ status: string; message: string } | null>(null)

const healthLoading = ref(false)
const health = ref<Record<string, { status: string; latency_ms: number }> | null>(null)
const healthLabels: Record<string, string> = {
  database: '数据库',
  llm: 'LLM 服务',
  anythingllm: 'AnythingLLM',
}

// 保存 setTimeout ID，组件卸载时清理
let saveMessageTimer: ReturnType<typeof setTimeout> | null = null

const showSkills = ref(false)
const skills = ref<AdminSkill[]>([])
const skillsLoading = ref(false)

const showSkillDialog = ref(false)
const skillForm = reactive({
  name: '',
  display_name: '',
  description: '',
  version: '1.0.0',
  author: '',
})

async function fetchStats() {
  try {
    const res = await getStats()
    stats.value = res.data.data
  } catch (e) {
    console.error(e)
  }
}

function maskKey(key: string): string {
  if (!key) return ''
  if (key.length <= 4) return '****'
  if (key.length <= 8) return key.slice(0, 2) + '****' + key.slice(-2)
  return key.slice(0, 4) + '****' + key.slice(-4)
}

async function fetchConfig() {
  configLoading.value = true
  try {
    const res = await getSystemConfig()
    config.value = res.data.data
    configForm.llm_base_url = res.data.data.llm_base_url || ''
    configForm.llm_model = res.data.data.llm_model || ''
    configForm.llm_api_key = ''
    configForm.anythingllm_base_url = res.data.data.anythingllm_base_url || ''
    configForm.anythingllm_api_key = ''
  } catch (e) {
    console.error(e)
  } finally {
    configLoading.value = false
  }
}

async function handleSaveConfig() {
  saving.value = true
  saveMessage.value = ''
  try {
        const payload: Record<string, string> = {}
    // 与当前配置对比，只发送有变化的字段
    if (configForm.llm_base_url !== (config.value.llm_base_url || '')) payload.llm_base_url = configForm.llm_base_url
    if (configForm.llm_model !== (config.value.llm_model || '')) payload.llm_model = configForm.llm_model
    if (configForm.llm_api_key !== '') payload.llm_api_key = configForm.llm_api_key
    if (configForm.anythingllm_base_url !== (config.value.anythingllm_base_url || '')) payload.anythingllm_base_url = configForm.anythingllm_base_url
    if (configForm.anythingllm_api_key !== '') payload.anythingllm_api_key = configForm.anythingllm_api_key
    if (Object.keys(payload).length === 0) {
      saveSuccess.value = false
      saveMessage.value = '未修改任何配置'
      return
    }
    await updateSystemConfig(payload)
    saveSuccess.value = true
    saveMessage.value = '保存成功'
    fetchConfig()
  } catch (e) {
    saveSuccess.value = false
    saveMessage.value = '保存失败'
    console.error(e)
    } finally {
    saving.value = false
    if (saveMessageTimer) clearTimeout(saveMessageTimer)
    saveMessageTimer = setTimeout(() => { saveMessage.value = '' }, 3000)
  }
}

async function handleTestLLM() {
  llmTesting.value = true
  llmTestResult.value = null
  try {
    const res = await testLLMConnection(
      configForm.llm_base_url,
      configForm.llm_api_key || 'test',
      configForm.llm_model
    )
    llmTestResult.value = res.data.data
  } catch (e) {
    llmTestResult.value = { status: 'error', message: '请求失败' }
    console.error(e)
  } finally {
    llmTesting.value = false
  }
}

async function handleTestAnythingLLM() {
  allmTesting.value = true
  allmTestResult.value = null
  try {
    const res = await testAnythingLLMConnection(
      configForm.anythingllm_base_url,
      configForm.anythingllm_api_key || 'test'
    )
    allmTestResult.value = res.data.data
  } catch (e) {
    allmTestResult.value = { status: 'error', message: '请求失败' }
    console.error(e)
  } finally {
    allmTesting.value = false
  }
}

async function fetchHealth() {
  healthLoading.value = true
  try {
    const res = await getHealthCheck()
    health.value = res.data.data
  } catch (e) {
    console.error(e)
  } finally {
    healthLoading.value = false
  }
}

async function fetchSkills() {
  skillsLoading.value = true
  try {
    const res = await getSkills()
    skills.value = res.data.data.items
  } catch (e) {
    console.error(e)
  } finally {
    skillsLoading.value = false
  }
}

async function handleCreateSkill() {
  if (!skillForm.name.trim() || !skillForm.display_name.trim()) return
  try {
    await createSkill({
      name: skillForm.name.trim(),
      display_name: skillForm.display_name.trim(),
      description: skillForm.description.trim() || undefined,
      version: skillForm.version.trim() || '1.0.0',
      author: skillForm.author.trim() || undefined,
    })
    showSkillDialog.value = false
    skillForm.name = ''
    skillForm.display_name = ''
    skillForm.description = ''
    skillForm.version = '1.0.0'
    skillForm.author = ''
    fetchSkills()
  } catch (e) {
    console.error(e)
  }
}

async function handleToggleSkill(skill: AdminSkill) {
  try {
    await toggleSkillEnabled(skill.id)
    fetchSkills()
  } catch (e) {
    console.error(e)
  }
}

async function handleDeleteSkill(skill: AdminSkill) {
  if (!confirm(`确定要删除技能 "${skill.display_name}" 吗？`)) return
  try {
    await deleteSkill(skill.id)
    fetchSkills()
  } catch (e) {
    console.error(e)
  }
}

onMounted(() => {
  fetchStats()
  fetchConfig()
  fetchHealth()
  fetchSkills()
})

onUnmounted(() => {
  if (saveMessageTimer) clearTimeout(saveMessageTimer)
})
</script>