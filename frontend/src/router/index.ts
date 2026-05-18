import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('../views/Login.vue'),
    },
    {
      path: '/',
      name: 'Chat',
      component: () => import('../views/Chat.vue'),
      meta: { requiresAuth: true },
    },
        {
      path: '/settings',
      name: 'UserSettings',
      component: () => import('../views/UserSettings.vue'),
      meta: { requiresAuth: true },
    },
        {
      path: '/share-access',
      name: 'ShareAccess',
      component: () => import('../views/ShareAccess.vue'),
    },
    {
      path: '/knowledge',
      component: () => import('../views/KnowledgeLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          name: 'KnowledgeManage',
          component: () => import('../views/admin/KnowledgeManage.vue'),
        },
      ],
    },
    {
      path: '/admin',
      component: () => import('../views/admin/AdminLayout.vue'),
      meta: { requiresAuth: true, requiresAdmin: true },
      children: [
        {
          path: '',
          redirect: '/admin/users',
        },
                {
          path: 'users',
          name: 'AdminUsers',
          component: () => import('../views/admin/UserManage.vue'),
        },
        {
          path: 'departments',
          name: 'AdminDepartments',
          component: () => import('../views/admin/DepartmentManage.vue'),
        },
        {
          path: 'knowledge',
          name: 'AdminKnowledge',
          component: () => import('../views/admin/KnowledgeManage.vue'),
        },
        {
          path: 'settings',
          name: 'AdminSettings',
          component: () => import('../views/admin/SystemSettings.vue'),
        },
        {
          path: 'audit-logs',
          name: 'AdminAuditLogs',
          component: () => import('../views/admin/AuditLogs.vue'),
        },
      ],
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'NotFound',
      redirect: '/',
    },
  ],
})

// 防止并发导航重复调用 fetchUser
let fetchingUser: Promise<boolean> | null = null

router.beforeEach(async (to) => {
  const authStore = useAuthStore()

  // 已登录用户访问 /login → 跳回首页
  if (to.name === 'Login' && authStore.token) {
    if (!authStore.user) {
      if (!fetchingUser) {
        fetchingUser = authStore.fetchUser().then(() => true)
      }
      await fetchingUser
      fetchingUser = null
    }
    return authStore.user ? { name: 'Chat' } : true
  }

  // 需要登录但没有 token → 跳登录页
  if (to.meta.requiresAuth && !authStore.token) {
    return { name: 'Login' }
  }

  // 已登录但 user 信息未加载（页面刷新），先拉取用户信息
  if (to.meta.requiresAuth && authStore.token && !authStore.user) {
    try {
      if (!fetchingUser) {
        fetchingUser = authStore.fetchUser().then(() => true)
      }
      await fetchingUser
    } finally {
      fetchingUser = null
    }
    // fetchUser 内部失败会调 logout() 清理 token，此时 user 为 null
    if (!authStore.user) {
      return { name: 'Login' }
    }
  }

  // 需要管理员权限但用户不是 admin 或 auditor（user 为 null 时也拒绝）
  if (to.meta.requiresAdmin && (!authStore.user || !['admin', 'auditor'].includes(authStore.user.role))) {
    return { name: 'Chat' }
  }
})

export default router
