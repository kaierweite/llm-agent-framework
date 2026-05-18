<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h2 class="text-xl font-semibold text-gray-800">部门管理</h2>
      <button @click="openCreateDialog(null)" class="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition">+ 新建部门</button>
    </div>

    <StatCards :stats="stats" />

    <div class="flex gap-6">
      <!-- 左侧：部门树 -->
      <div class="w-80 bg-white rounded-xl border border-gray-200 shrink-0 overflow-hidden flex flex-col" style="max-height: calc(100vh - 260px)">
        <div class="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
          <span class="text-sm font-medium text-gray-700">组织架构</span>
          <button @click="fetchTree" class="text-gray-400 hover:text-gray-600 transition" title="刷新">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
          </button>
        </div>
        <div v-if="treeLoading" class="p-8 text-center">
          <div class="inline-block w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
        </div>
        <div v-else-if="tree.length === 0" class="p-8 text-center text-gray-400 text-sm">暂无部门，点击"新建部门"开始</div>
        <div v-else class="overflow-y-auto flex-1 py-2">
          <TreeNode v-for="node in tree" :key="node.id" :node="node" :selected-id="selectedId" :depth="0" @select="selectDepartment" @create-child="openCreateDialog" @edit="openEditDialog" @delete="handleDelete" />
        </div>
      </div>

      <!-- 右侧：详情 -->
      <div class="flex-1 bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div v-if="!selectedDept" class="p-12 text-center">
          <svg class="w-12 h-12 mx-auto text-gray-300 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" /></svg>
          <p class="text-gray-400 text-lg">选择左侧部门查看详情</p>
        </div>

        <div v-else class="p-6">
          <div class="flex items-center justify-between mb-6">
            <div>
              <h3 class="text-lg font-semibold text-gray-800">{{ selectedDept.name }}</h3>
              <p class="text-sm text-gray-500 mt-1">编码：{{ selectedDept.code }}</p>
            </div>
            <div class="flex gap-2">
              <button @click="openEditDialog(selectedDept)" class="px-3 py-1.5 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 transition">编辑</button>
              <button @click="openCreateDialog(selectedDept)" class="px-3 py-1.5 text-sm text-blue-600 border border-blue-300 rounded-lg hover:bg-blue-50 transition">添加子部门</button>
            </div>
          </div>

          <div class="grid grid-cols-2 gap-4 mb-6 text-sm">
            <div class="bg-gray-50 rounded-lg p-3"><span class="text-gray-500">描述</span><p class="text-gray-800 mt-1">{{ selectedDept.description || '—' }}</p></div>
            <div class="bg-gray-50 rounded-lg p-3"><span class="text-gray-500">负责人</span><p class="text-gray-800 mt-1">{{ selectedDept.leader_email || '—' }}</p></div>
            <div class="bg-gray-50 rounded-lg p-3"><span class="text-gray-500">成员数</span><p class="text-gray-800 mt-1">{{ selectedDept.member_count }}</p></div>
            <div class="bg-gray-50 rounded-lg p-3"><span class="text-gray-500">状态</span><p class="mt-1"><span :class="selectedDept.is_active ? 'text-green-600' : 'text-red-500'">{{ selectedDept.is_active ? '启用' : '停用' }}</span></p></div>
          </div>

          <!-- 成员列表 -->
          <div>
            <div class="flex items-center justify-between mb-3">
              <h4 class="text-sm font-medium text-gray-700">部门成员</h4>
              <button @click="showAddMemberDialog = true" class="px-3 py-1 text-xs text-blue-600 border border-blue-300 rounded-lg hover:bg-blue-50 transition">添加成员</button>
            </div>
            <div v-if="membersLoading" class="p-4 text-center text-gray-400 text-sm">加载中...</div>
            <div v-else-if="members.length === 0" class="p-4 text-center text-gray-400 text-sm">暂无成员</div>
            <table v-else class="w-full text-sm">
              <thead class="bg-gray-50">
                <tr>
                  <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">邮箱</th>
                  <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">显示名</th>
                  <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">角色</th>
                  <th class="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">操作</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-100">
                <tr v-for="m in members" :key="m.id" class="hover:bg-gray-50">
                  <td class="px-4 py-2.5 text-gray-700">{{ m.email }}</td>
                  <td class="px-4 py-2.5 text-gray-600">{{ m.display_name || '—' }}</td>
                  <td class="px-4 py-2.5">
                    <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium" :class="m.role === 'admin' ? 'bg-purple-100 text-purple-700' : m.role === 'auditor' ? 'bg-amber-100 text-amber-700' : 'bg-blue-100 text-blue-700'">{{ m.role }}</span>
                  </td>
                  <td class="px-4 py-2.5 text-right">
                    <button @click="handleRemoveMember(m)" class="text-red-500 hover:text-red-700 text-xs">移除</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <!-- 创建/编辑对话框 -->
    <div v-if="showDialog" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40" @click.self="showDialog = false">
      <div class="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
        <h3 class="text-lg font-semibold text-gray-800 mb-4">{{ editingDept ? '编辑部门' : '新建部门' }}</h3>
        <div class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">部门名称 <span class="text-red-500">*</span></label>
            <input v-model="form.name" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none" placeholder="如：研发部" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">部门编码 <span class="text-red-500">*</span></label>
            <input v-model="form.code" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none" placeholder="如：RD（唯一标识）" :disabled="!!editingDept" />
            <p v-if="editingDept" class="text-xs text-gray-400 mt-1">编码创建后不可修改</p>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">描述</label>
            <textarea v-model="form.description" rows="2" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none resize-none" placeholder="部门职能描述（可选）"></textarea>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">上级部门</label>
            <select v-model="form.parent_id" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none bg-white">
              <option :value="null">无（顶级部门）</option>
              <option v-for="opt in parentOptions" :key="opt.id" :value="opt.id">{{ opt.label }}</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">排序</label>
            <input v-model.number="form.sort_order" type="number" min="0" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none" />
          </div>
          <div v-if="editingDept" class="flex items-center gap-2">
            <label class="text-sm font-medium text-gray-700">启用</label>
            <button @click="form.is_active = !form.is_active" class="relative inline-flex h-5 w-9 items-center rounded-full transition-colors" :class="form.is_active ? 'bg-blue-600' : 'bg-gray-300'">
              <span class="inline-block h-3.5 w-3.5 rounded-full bg-white transition-transform" :class="form.is_active ? 'translate-x-[18px]' : 'translate-x-[2px]'"></span>
            </button>
          </div>
        </div>
        <div class="flex justify-end gap-3 mt-6">
          <button @click="showDialog = false" class="px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 transition">取消</button>
          <button @click="handleSave" :disabled="saving" class="px-4 py-2 text-sm text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition disabled:opacity-50">{{ saving ? '保存中...' : '保存' }}</button>
        </div>
      </div>
    </div>

        <!-- 添加成员对话框 -->
    <div v-if="showAddMemberDialog" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40" @click.self="showAddMemberDialog = false">
      <div class="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
        <h3 class="text-lg font-semibold text-gray-800 mb-4">添加成员到「{{ selectedDept?.name }}」</h3>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">搜索或输入用户邮箱</label>
          <div class="relative">
            <input
              v-model="memberSearchQuery"
              type="text"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
              placeholder="输入邮箱搜索或直接输入新邮箱"
                            @focus="showMemberDropdown = true"
              @blur="closeMemberDropdown"
              @input="onMemberSearchInput"
            />
            <div v-if="showMemberDropdown && filteredUsers.length > 0" class="absolute z-10 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-48 overflow-y-auto">
              <div
                v-for="u in filteredUsers"
                :key="u.id"
                class="px-3 py-2 cursor-pointer hover:bg-blue-50 text-sm"
                :class="{ 'bg-blue-100': addMemberUserId === u.id }"
                @click="selectMemberUser(u)"
              >
                <div class="font-medium text-gray-800">{{ u.email }}</div>
                <div v-if="u.display_name" class="text-xs text-gray-500">{{ u.display_name }}</div>
              </div>
            </div>
          </div>
          <p v-if="memberSearchQuery && !addMemberUserId && isValidEmail(memberSearchQuery)" class="text-xs text-blue-600 mt-1">
            将使用邮箱「{{ memberSearchQuery }}」添加成员
          </p>
          <p v-if="filteredUsers.length === 0 && memberSearchQuery && !isValidEmail(memberSearchQuery)" class="text-xs text-red-500 mt-1">
            请输入有效的邮箱地址
          </p>
        </div>
        <div class="flex justify-end gap-3 mt-6">
          <button @click="showAddMemberDialog = false" class="px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 transition">取消</button>
          <button @click="handleAddMember" :disabled="!canAddMember" class="px-4 py-2 text-sm text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition disabled:opacity-50">添加</button>
        </div>
      </div>
    </div>

    <!-- Toast -->
    <div v-if="toast.show" class="fixed top-4 right-4 z-50 px-4 py-2.5 rounded-lg shadow-lg text-sm font-medium transition-all" :class="toast.type === 'success' ? 'bg-green-600 text-white' : 'bg-red-600 text-white'">{{ toast.message }}</div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import StatCards from '../../components/StatCards.vue'
import TreeNode from './DepartmentTreeNode.vue'
import { getDepartmentTree, getDepartment, createDepartment, updateDepartment, deleteDepartment, getDepartmentMembers, addDepartmentMember, removeDepartmentMember } from '../../api/department'
import { getUsers } from '../../api/admin'
import type { Department, DepartmentMember } from '../../api/department'
import type { AdminUser } from '../../api/admin'

const tree = ref<Department[]>([])
const treeLoading = ref(false)
const selectedId = ref<string | null>(null)
const selectedDept = ref<Department | null>(null)
const members = ref<DepartmentMember[]>([])
const membersLoading = ref(false)
const showDialog = ref(false)
const editingDept = ref<Department | null>(null)
const saving = ref(false)
const form = ref({ name: '', code: '', description: '', parent_id: null as string | null, sort_order: 0, is_active: true })
const showAddMemberDialog = ref(false)
const addMemberUserId = ref<string | null>(null)
const addMemberEmail = ref<string | null>(null)
const allUsers = ref<AdminUser[]>([])
const memberSearchQuery = ref('')
const showMemberDropdown = ref(false)
const toast = ref({ show: false, type: 'success' as 'success' | 'error', message: '' })
let toastTimer: ReturnType<typeof setTimeout> | null = null

const stats = computed(() => [
  { label: '部门总数', value: countAll(tree.value), color: 'blue' as const },
  { label: '已选中', value: selectedDept.value ? 1 : 0, color: 'green' as const },
  { label: '当前成员', value: members.value.length, color: 'purple' as const },
])

function countAll(nodes: Department[]): number {
  let c = 0
  for (const n of nodes) { c++; if (n.children) c += countAll(n.children) }
  return c
}

const parentOptions = computed(() => {
  const opts: { id: string; label: string }[] = []
  function walk(nodes: Department[], prefix: string) {
    for (const n of nodes) {
      if (editingDept.value && n.id === editingDept.value.id) continue
      opts.push({ id: n.id, label: prefix + n.name })
      if (n.children) walk(n.children, prefix + n.name + ' / ')
    }
  }
  walk(tree.value, '')
  return opts
})

const availableUsers = computed(() => {
  const ids = new Set(Array.isArray(members.value) ? members.value.map(m => m.id) : [])
  return Array.isArray(allUsers.value) ? allUsers.value.filter(u => !ids.has(u.id)) : []
})

const filteredUsers = computed(() => {
  if (!memberSearchQuery.value) return availableUsers.value
  const query = memberSearchQuery.value.toLowerCase()
  return availableUsers.value.filter(u =>
    u.email.toLowerCase().includes(query) ||
    (u.display_name && u.display_name.toLowerCase().includes(query))
  )
})

function isValidEmail(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
}

const canAddMember = computed(() => {
  return addMemberUserId.value || (memberSearchQuery.value && isValidEmail(memberSearchQuery.value))
})

function onMemberSearchInput() {
  addMemberUserId.value = null
  addMemberEmail.value = null
}

function selectMemberUser(user: AdminUser) {
  addMemberUserId.value = user.id
  addMemberEmail.value = user.email
  memberSearchQuery.value = user.email
  showMemberDropdown.value = false
}

function closeMemberDropdown() {
  setTimeout(() => { showMemberDropdown.value = false }, 200)
}

async function fetchTree() {
  treeLoading.value = true
  try { const res = await getDepartmentTree(); tree.value = res.data.data } catch { showToast('error', '加载部门树失败') } finally { treeLoading.value = false }
}

async function selectDepartment(id: string) {
  selectedId.value = id
  selectedDept.value = null
  membersLoading.value = true
  try {
    const [d, m] = await Promise.all([getDepartment(id), getDepartmentMembers(id)])
    selectedDept.value = d.data.data
    members.value = Array.isArray(m.data.data.items) ? m.data.data.items : []
  } catch { showToast('error', '加载部门详情失败') } finally { membersLoading.value = false }
}

async function fetchAllUsers() {
  try { 
    const res = await getUsers(1, 100)
    allUsers.value = Array.isArray(res.data.data.items) ? res.data.data.items : []
  } catch { /* ignore */ }
}

function openCreateDialog(parent: Department | null) {
  editingDept.value = null
  form.value = { name: '', code: '', description: '', parent_id: parent?.id || null, sort_order: 0, is_active: true }
  showDialog.value = true
}

function openEditDialog(dept: Department) {
  editingDept.value = dept
  form.value = { name: dept.name, code: dept.code, description: dept.description || '', parent_id: dept.parent_id, sort_order: dept.sort_order, is_active: dept.is_active }
  showDialog.value = true
}

async function handleSave() {
  if (!form.value.name.trim() || !form.value.code.trim()) { showToast('error', '名称和编码不能为空'); return }
  saving.value = true
  try {
    if (editingDept.value) {
      await updateDepartment(editingDept.value.id, { name: form.value.name, description: form.value.description || undefined, parent_id: form.value.parent_id, sort_order: form.value.sort_order, is_active: form.value.is_active })
      showToast('success', '部门已更新')
    } else {
      await createDepartment({ name: form.value.name, code: form.value.code, description: form.value.description || undefined, parent_id: form.value.parent_id, sort_order: form.value.sort_order })
      showToast('success', '部门已创建')
    }
    showDialog.value = false
    await fetchTree()
    if (selectedId.value) await selectDepartment(selectedId.value)
  } catch (e: unknown) { showToast('error', (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '操作失败') } finally { saving.value = false }
}

async function handleDelete(dept: Department) {
  if (!confirm(`确定要删除部门「${dept.name}」吗？子部门将被提升到上级，成员的部门关联将被清除。`)) return
  try {
    await deleteDepartment(dept.id)
    showToast('success', '部门已删除')
    if (selectedId.value === dept.id) { selectedId.value = null; selectedDept.value = null; members.value = [] }
    await fetchTree()
  } catch (e: unknown) { showToast('error', (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '删除失败') }
}

async function handleAddMember() {
  if (!selectedDept.value) return
  
  let userId = addMemberUserId.value
  let email = addMemberEmail.value || memberSearchQuery.value
  
  // 如果没有选择用户但输入了邮箱，尝试通过邮箱添加
  if (!userId && email && isValidEmail(email)) {
    // 需要后端支持通过邮箱添加成员，这里先用邮箱作为标识
    // 如果后端不支持，需要先查找用户ID
    const user = allUsers.value.find(u => u.email.toLowerCase() === email.toLowerCase())
    if (user) {
      userId = user.id
    } else {
      showToast('error', '未找到该邮箱对应的用户')
      return
    }
  }
  
  if (!userId) {
    showToast('error', '请选择或输入有效的用户')
    return
  }
  
  try {
    await addDepartmentMember(selectedDept.value.id, userId)
    showToast('success', '成员已添加')
    showAddMemberDialog.value = false
    addMemberUserId.value = null
    addMemberEmail.value = null
    memberSearchQuery.value = ''
    await selectDepartment(selectedDept.value.id)
    await fetchTree()
  } catch (e: unknown) { showToast('error', (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '操作失败') }
}

async function handleRemoveMember(member: DepartmentMember) {
  if (!selectedDept.value) return
  if (!confirm(`确定要将「${member.email}」从该部门移除吗？`)) return
  try {
    await removeDepartmentMember(selectedDept.value.id, member.id)
    showToast('success', '成员已移除')
    await selectDepartment(selectedDept.value.id)
    await fetchTree()
  } catch (e: unknown) { showToast('error', (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '操作失败') }
}

function showToast(type: 'success' | 'error', message: string) {
  if (toastTimer) clearTimeout(toastTimer)
  toast.value = { show: true, type, message }
  toastTimer = setTimeout(() => { toast.value.show = false }, 3000)
}

onMounted(() => { fetchTree(); fetchAllUsers() })
watch(showAddMemberDialog, (v) => { 
  if (v) {
    fetchAllUsers()
    memberSearchQuery.value = ''
    addMemberUserId.value = null
    addMemberEmail.value = null
    showMemberDropdown.value = false
  }
})
</script>
