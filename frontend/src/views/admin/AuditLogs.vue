<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h2 class="text-xl font-semibold text-gray-800">审计日志</h2>
      <div class="flex items-center gap-3">
        <select
          v-model="filterAction"
          class="border border-gray-300 rounded-lg px-3 py-1.5 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
          @change="fetchLogs(1)"
        >
                                        <option value="">全部操作</option>
          <option value="user.login">用户登录</option>
          <option value="user.register">用户注册</option>
          <option value="user.logout">用户登出</option>
          <option value="user.password_change">修改密码</option>
          <option value="admin.user_role_change">修改角色</option>
          <option value="admin.user_status_change">启用/禁用</option>
          <option value="admin.user_delete">删除用户</option>
          <option value="admin.user_password_reset">重置密码</option>
          <option value="admin.config_update">模型配置</option>
          <option value="admin.settings_update">系统设置</option>
          <option value="knowledge_base.create">创建知识库</option>
          <option value="knowledge_base.delete">删除知识库</option>
          <option value="knowledge_base.update">更新知识库</option>
          <option value="knowledge_base.share">分享知识库</option>
          <option value="document.upload">上传文档</option>
          <option value="document.delete">删除文档</option>
          <option value="conversation.create">创建对话</option>
          <option value="conversation.delete">删除对话</option>
          <option value="conversation.rename">重命名对话</option>
          <option value="message.feedback">消息反馈</option>
        </select>
      </div>
    </div>

    <div v-if="loading" class="text-center py-12 text-gray-500">加载中...</div>

    <div v-else-if="logs.length === 0" class="text-center py-12 text-gray-400">暂无审计日志</div>

    <div v-else class="bg-white rounded-lg border border-gray-200 overflow-hidden">
      <table class="w-full text-sm">
        <thead class="bg-gray-50 border-b border-gray-200">
          <tr>
            <th class="text-left px-4 py-3 font-medium text-gray-600">时间</th>
            <th class="text-left px-4 py-3 font-medium text-gray-600">用户</th>
            <th class="text-left px-4 py-3 font-medium text-gray-600">操作</th>
            <th class="text-left px-4 py-3 font-medium text-gray-600">详情</th>
            <th class="text-left px-4 py-3 font-medium text-gray-600">IP</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          <tr v-for="log in logs" :key="log.id" class="hover:bg-gray-50">
            <td class="px-4 py-3 text-gray-500 whitespace-nowrap">{{ formatTime(log.created_at) }}</td>
            <td class="px-4 py-3 text-gray-700">{{ log.user_email }}</td>
            <td class="px-4 py-3">
              <span
                class="inline-block px-2 py-0.5 rounded-full text-xs font-medium"
                :class="actionStyle(log.action)"
              >{{ actionLabel(log.action) }}</span>
            </td>
            <td class="px-4 py-3 text-gray-600 max-w-xs truncate">{{ log.detail || '-' }}</td>
            <td class="px-4 py-3 text-gray-400 text-xs">{{ log.ip_address || '-' }}</td>
          </tr>
        </tbody>
      </table>

      <div class="flex items-center justify-between px-4 py-3 border-t border-gray-200 bg-gray-50">
        <span class="text-sm text-gray-500">共 {{ total }} 条</span>
        <div class="flex items-center gap-2">
          <button
            :disabled="page <= 1"
            class="px-3 py-1 text-sm border border-gray-300 rounded disabled:opacity-40 disabled:cursor-not-allowed hover:bg-gray-100"
            @click="fetchLogs(page - 1)"
          >上一页</button>
          <span class="text-sm text-gray-600">{{ page }} / {{ totalPages }}</span>
          <button
            :disabled="page >= totalPages"
            class="px-3 py-1 text-sm border border-gray-300 rounded disabled:opacity-40 disabled:cursor-not-allowed hover:bg-gray-100"
            @click="fetchLogs(page + 1)"
          >下一页</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { getAuditLogs, type AuditLog } from '../../api/admin'

const logs = ref<AuditLog[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const loading = ref(true)
const filterAction = ref('')

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

async function fetchLogs(p: number) {
  loading.value = true
  try {
    const res = await getAuditLogs(p, pageSize, filterAction.value || undefined)
    logs.value = res.data.data.items
    total.value = res.data.data.total
    page.value = p
  } catch {
    logs.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function formatTime(iso: string) {
  if (!iso) return '-'
  const d = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

const ACTION_MAP: Record<string, string> = {
  'user.login': '用户登录',
  'user.register': '用户注册',
  'user.logout': '用户登出',
  'user.password_change': '修改密码',
  'admin.user_role_change': '修改角色',
  'admin.user_status_change': '启用/禁用',
  'admin.user_delete': '删除用户',
  'admin.user_password_reset': '重置密码',
  'admin.config_update': '模型配置',
  'admin.settings_update': '系统设置',
  'knowledge_base.create': '创建知识库',
  'knowledge_base.delete': '删除知识库',
  'knowledge_base.update': '更新知识库',
  'knowledge_base.share': '分享知识库',
  'document.upload': '上传文档',
  'document.delete': '删除文档',
  'conversation.create': '创建对话',
  'conversation.delete': '删除对话',
  'conversation.rename': '重命名对话',
  'message.feedback': '消息反馈',
}

function actionLabel(action: string) {
  return ACTION_MAP[action] || action
}

function actionStyle(action: string) {
  if (action.startsWith('user.login')) return 'bg-green-100 text-green-700'
  if (action.startsWith('user.register')) return 'bg-blue-100 text-blue-700'
  if (action.includes('delete')) return 'bg-red-100 text-red-700'
  if (action.includes('status') || action.includes('role')) return 'bg-yellow-100 text-yellow-700'
  if (action.includes('config') || action.includes('settings')) return 'bg-purple-100 text-purple-700'
  if (action.startsWith('knowledge_base.')) return 'bg-indigo-100 text-indigo-700'
  if (action.startsWith('document.')) return 'bg-cyan-100 text-cyan-700'
  if (action.startsWith('conversation.')) return 'bg-orange-100 text-orange-700'
  if (action.startsWith('message.')) return 'bg-pink-100 text-pink-700'
  return 'bg-gray-100 text-gray-700'
}

onMounted(() => fetchLogs(1))
</script>
