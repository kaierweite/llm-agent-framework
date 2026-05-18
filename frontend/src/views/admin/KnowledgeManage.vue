<template>
  <div class="min-h-screen bg-gradient-to-br from-slate-50 via-white to-indigo-50/30">
    <div class="max-w-[1400px] mx-auto px-6 py-8">
      <!-- Header -->
      <div class="mb-8">
        <div class="flex items-center gap-3 mb-1">
          <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-200">
            <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
            </svg>
          </div>
          <div>
            <h1 class="text-2xl font-bold bg-gradient-to-r from-gray-900 to-gray-600 bg-clip-text text-transparent">知识库管理</h1>
            <p class="text-sm text-gray-400">管理知识库和文档，支持 AI 问答检索</p>
          </div>
        </div>
      </div>

      <div class="flex gap-6 min-h-[calc(100vh-180px)]">
        <!-- Left: Knowledge Base Sidebar -->
        <div class="w-80 flex-shrink-0">
          <div class="bg-white/80 backdrop-blur-sm rounded-2xl shadow-sm border border-gray-100 overflow-hidden h-full flex flex-col">
            <!-- Sidebar Header -->
            <div class="p-5 border-b border-gray-100">
              <div class="flex items-center justify-between mb-3">
                <span class="text-sm font-semibold text-gray-700">知识库列表</span>
                <span class="text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">{{ kbTotal }} 个</span>
              </div>
              <button
                class="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium text-white bg-gradient-to-r from-indigo-500 to-purple-500 hover:from-indigo-600 hover:to-purple-600 shadow-md shadow-indigo-200/50 hover:shadow-lg hover:shadow-indigo-200 transition-all duration-200 active:scale-[0.98]"
                @click="showCreateModal = true"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                </svg>
                新建知识库
              </button>
            </div>
            <!-- KB List -->
            <div class="flex-1 overflow-y-auto p-2 space-y-1">
              <div v-if="bases.length === 0 && !loading" class="flex flex-col items-center justify-center py-12 text-gray-400">
                <svg class="w-12 h-12 mb-3 text-gray-200" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                </svg>
                <span class="text-sm">暂无知识库</span>
              </div>
              <div
                v-for="kb in bases"
                :key="kb.id"
                class="group relative px-4 py-3.5 rounded-xl cursor-pointer transition-all duration-200"
                :class="selectedKb?.id === kb.id
                  ? 'bg-gradient-to-r from-indigo-50 to-purple-50 border border-indigo-200/60 shadow-sm'
                  : 'hover:bg-gray-50 border border-transparent'"
                @click="selectKb(kb)"
              >
                <div v-if="selectedKb?.id === kb.id" class="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-gradient-to-b from-indigo-500 to-purple-500 rounded-r-full"></div>
                <div class="flex items-start justify-between">
                  <div class="min-w-0 flex-1 pl-1">
                    <div class="flex items-center gap-2">
                      <div class="w-8 h-8 rounded-lg flex items-center justify-center text-sm font-bold flex-shrink-0"
                        :class="selectedKb?.id === kb.id
                          ? 'bg-gradient-to-br from-indigo-500 to-purple-500 text-white'
                          : 'bg-gray-100 text-gray-500 group-hover:bg-indigo-100 group-hover:text-indigo-600'"
                      >
                        {{ kb.name.charAt(0).toUpperCase() }}
                      </div>
                                            <div class="min-w-0">
                        <div class="flex items-center gap-1.5">
                          <span class="text-sm font-medium truncate"
                            :class="selectedKb?.id === kb.id ? 'text-indigo-900' : 'text-gray-800'"
                          >{{ kb.name }}</span>
                          <span v-if="kb.is_shared" class="inline-flex items-center gap-0.5 px-1.5 py-0.5 text-[10px] font-medium rounded-full bg-amber-50 text-amber-600 border border-amber-200/60 shrink-0">
                            <svg class="w-2.5 h-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" /></svg>
                            分享
                          </span>
                        </div>
                        <div class="text-xs mt-0.5"
                          :class="selectedKb?.id === kb.id ? 'text-indigo-400' : 'text-gray-400'"
                        >
                          <template v-if="kb.is_shared && kb.shared_by">来自 {{ kb.shared_by }} · </template>{{ kb.document_count || 0 }} 个文档
                        </div>
                      </div>
                    </div>
                  </div>
                                    <div class="flex items-center gap-0.5 ml-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      v-if="kb.permission === 'owner' || kb.permission === 'admin'"
                      class="p-1.5 rounded-lg text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 transition-colors"
                      title="重命名"
                      @click.stop="startRename(kb)"
                    >
                      <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                      </svg>
                    </button>
                    <button
                      v-if="kb.permission === 'owner' || kb.permission === 'admin'"
                      class="p-1.5 rounded-lg text-gray-400 hover:text-red-500 hover:bg-red-50 transition-colors"
                      title="删除"
                      @click.stop="handleDeleteKb(kb)"
                    >
                      <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>
                </div>
              </div>
            </div>
            <!-- KB Pagination -->
            <div v-if="kbTotal > kbPageSize" class="p-3 border-t border-gray-100 flex items-center justify-between text-xs text-gray-400">
              <span>{{ kbPage }} / {{ Math.ceil(kbTotal / kbPageSize) }}</span>
              <div class="flex gap-1">
                <button class="px-2.5 py-1 rounded-lg hover:bg-gray-100 disabled:opacity-40 transition-colors" :disabled="kbPage <= 1" @click="kbPage--; fetchBases()">上一页</button>
                <button class="px-2.5 py-1 rounded-lg hover:bg-gray-100 disabled:opacity-40 transition-colors" :disabled="kbPage * kbPageSize >= kbTotal" @click="kbPage++; fetchBases()">下一页</button>
              </div>
            </div>
          </div>
        </div>

        <!-- Right: Document Area -->
        <div class="flex-1 min-w-0">
          <div class="bg-white/80 backdrop-blur-sm rounded-2xl shadow-sm border border-gray-100 overflow-hidden h-full flex flex-col">
            <!-- Doc Header -->
            <div class="px-6 py-5 border-b border-gray-100">
              <div class="flex items-center justify-between">
                <div>
                  <h2 class="text-lg font-bold text-gray-900">
                    <template v-if="selectedKb">
                      <span class="bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">{{ selectedKb.name }}</span>
                      <span class="text-gray-300 mx-2">·</span>
                      <span class="text-gray-500 font-normal text-base">文档管理</span>
                    </template>
                    <template v-else>
                      <span class="text-gray-400">请选择知识库</span>
                    </template>
                  </h2>
                  <p v-if="selectedKb && selectedKb.description" class="text-sm text-gray-400 mt-1">{{ selectedKb.description }}</p>
                </div>
                                <div v-if="selectedKb" class="flex items-center gap-2">
                                    <button
                    v-if="canEdit"
                    class="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium text-indigo-700 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200/60 transition-all duration-200 active:scale-[0.98]"
                    @click="openSharePanel"
                  >
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
                    </svg>
                    分享
                  </button>
                  <label
                    v-if="canEdit"
                    class="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium text-white bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-600 hover:to-teal-600 shadow-md shadow-emerald-200/50 hover:shadow-lg hover:shadow-emerald-200 transition-all duration-200 cursor-pointer active:scale-[0.98]"
                  >
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                    </svg>
                    上传文档
                    <input
                      type="file"
                      class="hidden"
                      accept=".txt,.md,.csv,.json,.log,.py,.js,.ts,.html,.xml,.yaml,.yml,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx"
                      @change="handleUpload"
                    />
                  </label>
                </div>
              </div>
            </div>

            <!-- Doc Content -->
            <div class="flex-1 overflow-y-auto">
              <!-- Empty State -->
              <div v-if="!selectedKb" class="flex flex-col items-center justify-center h-full py-20">
                <div class="w-20 h-20 rounded-2xl bg-gradient-to-br from-indigo-100 to-purple-100 flex items-center justify-center mb-4">
                  <svg class="w-10 h-10 text-indigo-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                  </svg>
                </div>
                <p class="text-gray-400 text-sm">从左侧选择一个知识库</p>
              </div>

              <div v-else-if="documents.length === 0 && !docLoading" class="flex flex-col items-center justify-center h-full py-20">
                <div class="w-20 h-20 rounded-2xl bg-gradient-to-br from-emerald-100 to-teal-100 flex items-center justify-center mb-4">
                  <svg class="w-10 h-10 text-emerald-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <p class="text-gray-400 text-sm mb-1">暂无文档</p>
                <p class="text-gray-300 text-xs">点击右上角"上传文档"添加</p>
              </div>

              <!-- Document Cards -->
              <div v-else class="p-4 space-y-3">
                <div
                  v-for="doc in documents"
                  :key="doc.id"
                  class="group relative flex items-center gap-4 px-5 py-4 rounded-xl border border-gray-100 hover:border-indigo-200/60 hover:bg-indigo-50/30 transition-all duration-200"
                >
                  <!-- File Icon -->
                  <div class="w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0"
                    :class="getFileIconClass(doc.file_type)"
                  >
                    <span class="text-xs font-bold uppercase">{{ getFileExt(doc.file_type) }}</span>
                  </div>

                  <!-- File Info -->
                  <div class="flex-1 min-w-0">
                    <div class="text-sm font-medium text-gray-800 truncate group-hover:text-indigo-900 transition-colors">{{ doc.filename }}</div>
                    <div class="flex items-center gap-3 mt-1.5">
                      <span class="text-xs text-gray-400">{{ formatFileSize(doc.file_size) }}</span>
                      <span class="text-xs text-gray-300">·</span>
                      <span class="text-xs text-gray-400">{{ formatTime(doc.created_at) }}</span>
                    </div>
                  </div>

                  <!-- Status -->
                  <div class="flex-shrink-0">
                    <span
                      class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium"
                      :class="getStatusClass(doc.upload_status)"
                    >
                      <span class="w-1.5 h-1.5 rounded-full" :class="getStatusDotClass(doc.upload_status)"></span>
                      {{ statusText(doc.upload_status) }}
                    </span>
                  </div>

                                    <!-- Actions -->
                  <div class="flex items-center gap-1 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      class="p-2 rounded-lg text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 transition-colors"
                      title="预览"
                      @click="handlePreview(doc)"
                    >
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                      </svg>
                    </button>
                    <button
                      v-if="canEdit"
                      class="p-2 rounded-lg text-gray-400 hover:text-red-500 hover:bg-red-50 transition-colors"
                      title="删除"
                      @click="handleDeleteDoc(doc)"
                    >
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <!-- Doc Pagination -->
            <div v-if="docTotal > docPageSize" class="px-6 py-3 border-t border-gray-100 flex items-center justify-between text-xs text-gray-400">
              <span>共 {{ docTotal }} 个文档</span>
              <div class="flex gap-1">
                <button class="px-3 py-1.5 rounded-lg hover:bg-gray-100 disabled:opacity-40 transition-colors" :disabled="docPage <= 1" @click="docPage--; fetchDocuments()">上一页</button>
                <button class="px-3 py-1.5 rounded-lg hover:bg-gray-100 disabled:opacity-40 transition-colors" :disabled="docPage * docPageSize >= docTotal" @click="docPage++; fetchDocuments()">下一页</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Create Modal -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="showCreateModal" class="fixed inset-0 z-50 flex items-center justify-center p-4" @click.self="showCreateModal = false">
          <div class="absolute inset-0 bg-black/40 backdrop-blur-sm"></div>
          <div class="relative bg-white rounded-2xl shadow-2xl w-full max-w-md p-0 overflow-hidden">
            <div class="bg-gradient-to-r from-indigo-500 to-purple-500 px-6 py-5">
              <h3 class="text-lg font-semibold text-white">新建知识库</h3>
              <p class="text-sm text-white/70 mt-0.5">创建一个新的知识库来组织你的文档</p>
            </div>
            <div class="p-6">
              <label class="block text-sm font-medium text-gray-700 mb-1.5">名称</label>
              <input
                v-model="newKbName"
                class="w-full px-4 py-2.5 border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 outline-none transition-all bg-gray-50 focus:bg-white"
                placeholder="例如：产品文档库"
                @keyup.enter="handleCreateKb"
              />
                            <label class="block text-sm font-medium text-gray-700 mb-1.5 mt-4">描述（可选）</label>
              <textarea
                v-model="newKbDesc"
                class="w-full px-4 py-2.5 border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 outline-none resize-none transition-all bg-gray-50 focus:bg-white"
                rows="3"
                placeholder="简单描述这个知识库的用途"
              ></textarea>
              <!-- 聊天设置 -->
              <div class="mt-4 p-4 bg-gray-50 rounded-xl border border-gray-200">
                <div class="flex items-center gap-2 mb-3">
                  <svg class="w-4 h-4 text-indigo-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                  <span class="text-sm font-medium text-gray-700">聊天模型设置</span>
                  <span class="text-xs text-gray-400">（可选，不填使用全局默认）</span>
                </div>
                <label class="block text-xs font-medium text-gray-500 mb-1">模型提供商</label>
                <select
                  v-model="newKbChatProvider"
                  class="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 outline-none transition-all bg-white"
                >
                  <option value="">使用全局默认</option>
                  <option value="lmstudio">LM Studio</option>
                  <option value="openai">OpenAI</option>
                  <option value="ollama">Ollama</option>
                  <option value="anthropic">Anthropic</option>
                  <option value="custom">自定义</option>
                </select>
                <label class="block text-xs font-medium text-gray-500 mb-1 mt-3">模型名称</label>
                <input
                  v-model="newKbChatModel"
                  class="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 outline-none transition-all bg-white"
                  placeholder="例如：qwen/qwen3.5-9b"
                />
              </div>
              <div class="flex justify-end gap-2 mt-6">
                <button class="px-5 py-2.5 text-sm text-gray-600 hover:bg-gray-100 rounded-xl transition-colors" @click="showCreateModal = false">取消</button>
                <button class="px-5 py-2.5 text-sm font-medium text-white bg-gradient-to-r from-indigo-500 to-purple-500 hover:from-indigo-600 hover:to-purple-600 rounded-xl shadow-md shadow-indigo-200/50 transition-all active:scale-[0.98]" @click="handleCreateKb">创建</button>
              </div>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- Rename Modal -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="renamingKb" class="fixed inset-0 z-50 flex items-center justify-center p-4" @click.self="renamingKb = null">
          <div class="absolute inset-0 bg-black/40 backdrop-blur-sm"></div>
          <div class="relative bg-white rounded-2xl shadow-2xl w-full max-w-md p-6">
            <h3 class="text-lg font-semibold text-gray-900 mb-4">重命名知识库</h3>
            <input
              v-model="renameName"
              class="w-full px-4 py-2.5 border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 outline-none transition-all bg-gray-50 focus:bg-white"
              placeholder="新名称"
              @keyup.enter="handleRename"
            />
            <div class="flex justify-end gap-2 mt-5">
              <button class="px-5 py-2.5 text-sm text-gray-600 hover:bg-gray-100 rounded-xl transition-colors" @click="renamingKb = null">取消</button>
              <button class="px-5 py-2.5 text-sm font-medium text-white bg-gradient-to-r from-indigo-500 to-purple-500 hover:from-indigo-600 hover:to-purple-600 rounded-xl shadow-md transition-all active:scale-[0.98]" @click="handleRename">保存</button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- Preview Modal -->
    <Teleport to="body">
      <Transition name="modal">
                <div v-if="previewDoc" class="fixed inset-0 z-50 flex items-center justify-center p-4" :class="{ 'p-0': previewFullscreen }" @click.self="previewDoc = null; previewFullscreen = false">
          <div class="absolute inset-0 bg-black/40 backdrop-blur-sm"></div>
          <div class="relative bg-white rounded-2xl shadow-2xl flex flex-col overflow-hidden transition-all duration-300"
            :class="previewFullscreen ? 'w-full h-full rounded-none' : 'w-full max-w-4xl max-h-[85vh]'"
          >
            <div class="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
              <div class="flex items-center gap-3 min-w-0">
                <div class="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0"
                  :class="getFileIconClass(previewDoc.file_type)"
                >
                  <span class="text-[10px] font-bold uppercase">{{ getFileExt(previewDoc.file_type) }}</span>
                </div>
                <h3 class="font-semibold text-gray-900 truncate">{{ previewDoc.filename }}</h3>
              </div>
              <div class="flex items-center gap-1">
                <button class="p-2 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors" @click="previewFullscreen = !previewFullscreen" :title="previewFullscreen ? '退出全屏' : '放大预览'">
                  <!-- 放大图标 -->
                  <svg v-if="!previewFullscreen" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4"/></svg>
                  <!-- 缩小图标 -->
                  <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 9V4.5M9 9H4.5M9 9L3.75 3.75M9 15v4.5M9 15H4.5M9 15l-5.25 5.25M15 9h4.5M15 9V4.5M15 9l5.25-5.25M15 15h4.5M15 15v4.5m0-4.5l5.25 5.25"/></svg>
                </button>
                <button class="p-2 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors" @click="previewDoc = null; previewFullscreen = false">
                  <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
                </button>
              </div>
            </div>
                                                <div class="flex-1 overflow-auto" :class="previewFullscreen ? 'p-0' : 'p-6'">
              <DocumentPreview
                :preview-data="previewData"
                :loading="previewLoading"
                :error="previewError"
              />
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

        <!-- Share Panel Modal -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="showSharePanel" class="fixed inset-0 z-50 flex items-center justify-center p-4" @click.self="showSharePanel = false">
          <div class="absolute inset-0 bg-black/40 backdrop-blur-sm"></div>
          <div class="relative bg-white rounded-2xl shadow-2xl w-full max-w-lg p-0 overflow-hidden">
            <div class="bg-gradient-to-r from-indigo-500 to-purple-500 px-6 py-5 flex items-center justify-between">
              <div>
                <h3 class="text-lg font-semibold text-white">分享知识库</h3>
                <p class="text-sm text-white/70 mt-0.5">{{ sharePanelKb?.name }}</p>
              </div>
              <button class="p-2 rounded-lg text-white/70 hover:text-white hover:bg-white/10 transition-colors" @click="showSharePanel = false">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
              </button>
            </div>

            <div class="p-6">
              <!-- 生成分享码 -->
              <div class="mb-6">
                <p class="text-sm font-medium text-gray-700 mb-3">创建分享码</p>
                <div class="flex gap-2">
                  <select
                    v-model="sharePermission"
                    class="flex-1 px-3 py-2.5 border border-gray-200 rounded-xl text-sm bg-gray-50 focus:bg-white focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 outline-none transition-all"
                  >
                    <option value="read">只读（查看知识库信息和文档）</option>
                    <option value="query">可问答（允许通过分享码进行问答）</option>
                  </select>
                  <button
                    class="px-5 py-2.5 rounded-xl text-sm font-medium text-white bg-gradient-to-r from-indigo-500 to-purple-500 hover:from-indigo-600 hover:to-purple-600 shadow-md shadow-indigo-200/50 transition-all active:scale-[0.98] whitespace-nowrap"
                    :disabled="generatingCode"
                    @click="handleGenerateCode"
                  >
                    <span v-if="generatingCode" class="flex items-center gap-1.5">
                      <svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
                      生成中
                    </span>
                    <span v-else>生成分享码</span>
                  </button>
                </div>
              </div>

              <!-- 分享码列表 -->
              <div>
                <div class="flex items-center justify-between mb-3">
                  <p class="text-sm font-medium text-gray-700">已有的分享码</p>
                  <button
                    class="text-xs text-gray-400 hover:text-indigo-500 transition-colors"
                    @click="fetchShareCodes"
                  >
                    刷新
                  </button>
                </div>

                <div v-if="shareCodesLoading" class="flex items-center justify-center py-8">
                  <div class="w-6 h-6 border-2 border-indigo-200 border-t-indigo-500 rounded-full animate-spin"></div>
                </div>

                <div v-else-if="shareCodes.length === 0" class="text-center py-8 text-gray-400 text-sm">
                  暂无分享码
                </div>

                <div v-else class="space-y-2 max-h-60 overflow-y-auto">
                  <div
                    v-for="code in shareCodes"
                    :key="code.id"
                    class="flex items-center gap-3 px-4 py-3 rounded-xl border transition-all"
                    :class="code.is_active && !code.is_expired
                      ? 'border-gray-100 bg-gray-50/50 hover:bg-gray-50'
                      : 'border-gray-100 bg-gray-50/30 opacity-60'"
                  >
                    <div class="flex-1 min-w-0">
                      <div class="flex items-center gap-2 mb-1">
                        <code class="text-sm font-mono font-semibold text-gray-800 tracking-wider">{{ code.share_code }}</code>
                        <button
                          class="p-0.5 rounded text-gray-400 hover:text-indigo-500 transition-colors"
                          title="复制分享码"
                          @click="copyShareCode(code.share_code)"
                        >
                          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                          </svg>
                        </button>
                      </div>
                      <div class="flex items-center gap-2 text-xs text-gray-400">
                        <span class="px-1.5 py-0.5 rounded bg-gray-100">{{ code.permission === 'query' ? '可问答' : '只读' }}</span>
                        <span v-if="code.is_expired" class="text-red-400">已过期</span>
                        <span v-else-if="!code.is_active" class="text-gray-400">已吊销</span>
                        <span v-else-if="code.expires_at">到期 {{ formatExpiry(code.expires_at) }}</span>
                        <span v-if="code.created_at">· 创建于 {{ formatTime(code.created_at) }}</span>
                      </div>
                    </div>
                    <button
                      v-if="code.is_active && !code.is_expired"
                      class="px-3 py-1.5 rounded-lg text-xs font-medium text-red-500 hover:text-white hover:bg-red-500 border border-red-200 hover:border-red-500 transition-all"
                      @click="handleRevokeCode(code)"
                    >
                      吊销
                    </button>
                  </div>
                </div>
              </div>

              <!-- 成员管理 -->
              <div class="mt-6 pt-6 border-t border-gray-100">
                <div class="flex items-center justify-between mb-3">
                  <p class="text-sm font-medium text-gray-700">成员管理</p>
                  <button
                    class="px-3 py-1.5 text-xs text-indigo-600 border border-indigo-300 rounded-lg hover:bg-indigo-50 transition"
                    @click="showAddMemberDialog = true"
                  >
                    添加成员
                  </button>
                </div>

                <div v-if="membersLoading" class="flex items-center justify-center py-8">
                  <div class="w-6 h-6 border-2 border-indigo-200 border-t-indigo-500 rounded-full animate-spin"></div>
                </div>

                <div v-else-if="members.length === 0" class="text-center py-8 text-gray-400 text-sm">
                  暂无成员
                </div>

                <div v-else class="space-y-2 max-h-48 overflow-y-auto">
                  <div
                    v-for="member in members"
                    :key="member.user_id"
                    class="flex items-center gap-3 px-4 py-3 rounded-xl border border-gray-100 bg-gray-50/50 hover:bg-gray-50 transition-all"
                  >
                    <div class="flex-1 min-w-0">
                      <div class="flex items-center gap-2">
                        <div class="w-7 h-7 rounded-full bg-gradient-to-br from-indigo-400 to-purple-400 flex items-center justify-center text-white text-xs font-bold">
                          {{ member.email.charAt(0).toUpperCase() }}
                        </div>
                        <div class="min-w-0 flex-1">
                          <div class="text-sm font-medium text-gray-800 truncate">{{ member.display_name || member.email }}</div>
                          <div class="text-xs text-gray-400 truncate">{{ member.email }}</div>
                        </div>
                      </div>
                    </div>
                    <div class="flex items-center gap-2">
                      <select
                        :value="member.permission"
                        class="px-2 py-1.5 text-xs border border-gray-200 rounded-lg bg-white focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 outline-none transition-all"
                        @change="handleUpdatePermission(member.user_id, ($event.target as HTMLSelectElement).value)"
                      >
                        <option value="read">只读</option>
                        <option value="write">可编辑</option>
                        <option value="admin">管理员</option>
                      </select>
                      <button
                        class="p-1.5 rounded-lg text-gray-400 hover:text-red-500 hover:bg-red-50 transition-colors"
                        title="移除成员"
                        @click="handleRemoveMember(member)"
                      >
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                        </svg>
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 访问日志入口 -->
              <div class="mt-6 pt-6 border-t border-gray-100">
                <button
                  class="text-sm text-indigo-500 hover:text-indigo-600 font-medium transition-colors"
                  @click="openAccessLogs"
                >
                  查看访问日志 →
                </button>
              </div>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- 添加成员对话框 -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="showAddMemberDialog" class="fixed inset-0 z-50 flex items-center justify-center p-4" @click.self="showAddMemberDialog = false">
          <div class="absolute inset-0 bg-black/40 backdrop-blur-sm"></div>
          <div class="relative bg-white rounded-2xl shadow-2xl w-full max-w-md p-0 overflow-hidden">
            <div class="bg-gradient-to-r from-indigo-500 to-purple-500 px-6 py-5 flex items-center justify-between">
              <div>
                <h3 class="text-lg font-semibold text-white">添加成员</h3>
                <p class="text-sm text-white/70 mt-0.5">{{ sharePanelKb?.name }}</p>
              </div>
              <button class="p-2 rounded-lg text-white/70 hover:text-white hover:bg-white/10 transition-colors" @click="showAddMemberDialog = false">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
              </button>
            </div>

            <div class="p-6">
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">搜索或输入用户邮箱</label>
                <div class="relative">
                  <input
                    v-model="memberSearchQuery"
                    type="text"
                    class="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all"
                    placeholder="输入邮箱搜索或直接输入新邮箱"
                    @focus="showMemberDropdown = true"
                    @blur="closeMemberDropdown"
                    @input="onMemberSearchInput"
                  />
                  <div v-if="showMemberDropdown && filteredUsers.length > 0" class="absolute z-20 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-48 overflow-y-auto">
                    <div
                      v-for="u in filteredUsers"
                      :key="u.id"
                      class="px-3 py-2 cursor-pointer hover:bg-indigo-50 text-sm"
                      :class="{ 'bg-indigo-100': addMemberUserId === u.id }"
                      @click="selectMemberUser(u)"
                    >
                      <div class="font-medium text-gray-800">{{ u.email }}</div>
                      <div v-if="u.display_name" class="text-xs text-gray-500">{{ u.display_name }}</div>
                    </div>
                  </div>
                </div>
                <p v-if="memberSearchQuery && !addMemberUserId && isValidEmail(memberSearchQuery)" class="text-xs text-indigo-600 mt-1">
                  将使用邮箱「{{ memberSearchQuery }}」添加成员
                </p>
                <p v-if="filteredUsers.length === 0 && memberSearchQuery && !isValidEmail(memberSearchQuery)" class="text-xs text-red-500 mt-1">
                  请输入有效的邮箱地址
                </p>
              </div>

              <div class="mt-4">
                <label class="block text-sm font-medium text-gray-700 mb-1">权限</label>
                <select
                  v-model="addMemberPermission"
                  class="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all"
                >
                  <option value="read">只读（查看知识库信息和文档）</option>
                  <option value="write">可编辑（上传/删除文档）</option>
                  <option value="admin">管理员（管理成员和权限）</option>
                </select>
              </div>
            </div>

            <div class="px-6 py-4 border-t border-gray-100 flex justify-end gap-3">
              <button
                class="px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 transition"
                @click="showAddMemberDialog = false"
              >
                取消
              </button>
              <button
                class="px-5 py-2 text-sm font-medium text-white bg-gradient-to-r from-indigo-500 to-purple-500 rounded-lg hover:from-indigo-600 hover:to-purple-600 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                :disabled="!canAddMember || addingMember"
                @click="handleAddMember"
              >
                {{ addingMember ? '添加中...' : '添加' }}
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- Access Logs Modal -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="showAccessLogs" class="fixed inset-0 z-50 flex items-center justify-center p-4" @click.self="showAccessLogs = false">
          <div class="absolute inset-0 bg-black/40 backdrop-blur-sm"></div>
          <div class="relative bg-white rounded-2xl shadow-2xl w-full max-w-3xl max-h-[80vh] flex flex-col overflow-hidden">
            <div class="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
              <div>
                <h3 class="text-lg font-semibold text-gray-900">访问日志</h3>
                <p class="text-sm text-gray-400 mt-0.5">{{ accessLogsKb?.name }}</p>
              </div>
              <button class="p-2 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors" @click="showAccessLogs = false">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
              </button>
            </div>
            <div class="flex-1 overflow-y-auto">
              <div v-if="accessLogsLoading" class="flex items-center justify-center py-16">
                <div class="w-8 h-8 border-2 border-indigo-200 border-t-indigo-500 rounded-full animate-spin"></div>
              </div>
              <div v-else-if="accessLogs.length === 0" class="flex flex-col items-center justify-center py-16 text-gray-400">
                <svg class="w-12 h-12 mb-3 text-gray-200" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
                <span class="text-sm">暂无访问记录</span>
              </div>
              <table v-else class="w-full text-sm">
                <thead class="bg-gray-50 text-gray-500 text-xs uppercase">
                  <tr>
                    <th class="px-6 py-3 text-left font-medium">用户</th>
                    <th class="px-6 py-3 text-left font-medium">操作</th>
                    <th class="px-6 py-3 text-left font-medium">详情</th>
                    <th class="px-6 py-3 text-left font-medium">分享码</th>
                    <th class="px-6 py-3 text-left font-medium">时间</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-gray-100">
                  <tr v-for="log in accessLogs" :key="log.id" class="hover:bg-gray-50 transition-colors">
                    <td class="px-6 py-3">
                      <div class="font-medium text-gray-800">{{ log.display_name || log.email }}</div>
                      <div class="text-xs text-gray-400">{{ log.email }}</div>
                    </td>
                    <td class="px-6 py-3">
                      <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium"
                        :class="{
                          'bg-blue-50 text-blue-700': log.action === 'view',
                          'bg-purple-50 text-purple-700': log.action === 'query',
                          'bg-green-50 text-green-700': log.action === 'download',
                          'bg-amber-50 text-amber-700': log.action === 'share',
                        }"
                      >
                        {{ actionText(log.action) }}
                      </span>
                    </td>
                    <td class="px-6 py-3 text-gray-500 max-w-[200px] truncate">{{ log.detail || '-' }}</td>
                    <td class="px-6 py-3 font-mono text-xs text-gray-500">{{ log.share_code || '-' }}</td>
                    <td class="px-6 py-3 text-gray-400 whitespace-nowrap">{{ log.created_at ? formatTime(log.created_at) : '-' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div v-if="accessLogsTotal > 20" class="px-6 py-3 border-t border-gray-100 flex items-center justify-between text-xs text-gray-400">
              <span>共 {{ accessLogsTotal }} 条记录</span>
              <div class="flex gap-1">
                <button class="px-3 py-1.5 rounded-lg hover:bg-gray-100 disabled:opacity-40 transition-colors" :disabled="accessLogsPage <= 1" @click="accessLogsPage--; fetchAccessLogs()">上一页</button>
                <button class="px-3 py-1.5 rounded-lg hover:bg-gray-100 disabled:opacity-40 transition-colors" :disabled="accessLogsPage * 20 >= accessLogsTotal" @click="accessLogsPage++; fetchAccessLogs()">下一页</button>
              </div>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- Toast -->
    <Teleport to="body">
      <Transition name="toast">
        <div v-if="toast" class="fixed top-6 right-6 z-[100] flex items-center gap-3 px-5 py-3.5 rounded-xl shadow-xl text-sm font-medium backdrop-blur-sm"
          :class="{
            'bg-emerald-500/90 text-white': toast.type === 'success',
            'bg-red-500/90 text-white': toast.type === 'error',
          }"
        >
          <svg v-if="toast.type === 'success'" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          {{ toast.message }}
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import {
  listKnowledgeBases,
  getKnowledgeBase,
  createKnowledgeBase,
  renameKnowledgeBase,
  deleteKnowledgeBase,
  listDocuments,
  uploadDocument,
  deleteDocument,
  previewDocument,
} from '@/api/knowledge'
import DocumentPreview from '@/components/DocumentPreview.vue'
import {
  generateShareCode,
  revokeShareCode,
  listShareCodes,
  listAccessLogs,
} from '@/api/kbShare'
import type { ShareCode, AccessLog } from '@/types'
import {
  listKnowledgeBaseMembers,
  addKnowledgeBaseMember,
  removeKnowledgeBaseMember,
  updateKnowledgeBaseMemberPermission,
  type KnowledgeBaseMember,
} from '@/api/knowledge'
import { listAllUsers } from '@/api/knowledge'

interface KnowledgeBaseItem {
  id: string
  name: string
  description: string
  document_count: number
  is_active: boolean
  is_owner?: boolean
  permission?: string  // owner | admin | write | read
  created_at: string
  updated_at: string
}

interface KnowledgeDocument {
  id: string
  filename: string
  file_size: number
  file_type: string
  upload_status: string
  error_message: string | null
  created_at: string
  updated_at: string
}

const bases = ref<KnowledgeBaseItem[]>([])
const selectedKb = ref<KnowledgeBaseItem | null>(null)
const documents = ref<KnowledgeDocument[]>([])
const kbPage = ref(1)
const kbPageSize = 20
const kbTotal = ref(0)
const docPage = ref(1)
const docPageSize = 20
const docTotal = ref(0)
const loading = ref(false)
const docLoading = ref(false)

const showCreateModal = ref(false)
const newKbName = ref('')
const newKbDesc = ref('')
const newKbChatProvider = ref('')
const newKbChatModel = ref('')

const renamingKb = ref<KnowledgeBaseItem | null>(null)
const renameName = ref('')

const previewDoc = ref<KnowledgeDocument | null>(null)
const previewData = ref<any>(null)
const previewLoading = ref(false)
const previewError = ref<string | null>(null)
const previewFullscreen = ref(false)

const toast = ref<{ type: string; message: string } | null>(null)

// ── 分享相关状态 ──
const showSharePanel = ref(false)
const sharePanelKb = ref<KnowledgeBaseItem | null>(null)
const sharePermission = ref('read')
const generatingCode = ref(false)
const shareCodes = ref<ShareCode[]>([])
const shareCodesLoading = ref(false)

const showAccessLogs = ref(false)
const accessLogsKb = ref<KnowledgeBaseItem | null>(null)
const accessLogs = ref<AccessLog[]>([])
const accessLogsLoading = ref(false)
const accessLogsTotal = ref(0)
const accessLogsPage = ref(1)

// 成员管理
const members = ref<KnowledgeBaseMember[]>([])
const membersLoading = ref(false)
const showAddMemberDialog = ref(false)
const addingMember = ref(false)
const memberSearchQuery = ref('')
const addMemberUserId = ref<string | null>(null)
const addMemberEmail = ref<string | null>(null)
const addMemberPermission = ref('read')
const showMemberDropdown = ref(false)
const allUsers = ref<Array<{ id: string; email: string; display_name: string | null }>>([])

let pollTimer: ReturnType<typeof setInterval> | null = null

// 当前用户对选中知识库的编辑权限
const canEdit = computed(() => {
  if (!selectedKb.value) return false
  const perm = selectedKb.value.permission
  return perm === 'owner' || perm === 'admin' || perm === 'write'
})

function showToast(type: string, message: string) {
  toast.value = { type, message }
  setTimeout(() => { toast.value = null }, 3000)
}

function extractErrorMessage(err: unknown, fallback: string): string {
  if (err && typeof err === 'object') {
    const e = err as Record<string, unknown>
    const detail = e.response?.data?.detail
    if (detail && typeof detail === 'object' && 'message' in detail) {
      return (detail as { message: string }).message
    }
    if (typeof detail === 'string') return detail
    if (e.message) return String(e.message)
  }
  return fallback
}

function formatFileSize(bytes: number | null | undefined): string {
  if (!bytes) return '-'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1024 / 1024).toFixed(1) + ' MB'
}

function formatTime(t: string) {
  if (!t) return '-'
  return new Date(t).toLocaleString('zh-CN')
}

function statusText(s: string) {
  const map: Record<string, string> = {
    ready: '就绪',
    uploading: '上传中',
    embedding: '向量化中',
    pending: '等待中',
    processing: '处理中',
    failed: '失败',
  }
  return map[s] || s
}

function getFileExt(type: string | null): string {
  if (!type) return '?'
  return type.replace('.', '').substring(0, 4)
}

function getFileIconClass(type: string | null): string {
  const ext = (type || '').toLowerCase()
  if (ext.includes('pdf')) return 'bg-red-100 text-red-600'
  if (ext.includes('doc')) return 'bg-blue-100 text-blue-600'
  if (ext.includes('xls')) return 'bg-emerald-100 text-emerald-600'
  if (ext.includes('ppt')) return 'bg-orange-100 text-orange-600'
  if (ext.includes('json') || ext.includes('csv')) return 'bg-amber-100 text-amber-600'
  if (ext.includes('py') || ext.includes('js') || ext.includes('ts')) return 'bg-indigo-100 text-indigo-600'
  if (ext.includes('html') || ext.includes('xml')) return 'bg-cyan-100 text-cyan-600'
  return 'bg-gray-100 text-gray-500'
}

function getStatusClass(s: string): string {
  const map: Record<string, string> = {
    ready: 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200/60',
    uploading: 'bg-amber-50 text-amber-700 ring-1 ring-amber-200/60',
    embedding: 'bg-indigo-50 text-indigo-700 ring-1 ring-indigo-200/60',
    pending: 'bg-gray-50 text-gray-600 ring-1 ring-gray-200/60',
    processing: 'bg-blue-50 text-blue-700 ring-1 ring-blue-200/60',
    failed: 'bg-red-50 text-red-700 ring-1 ring-red-200/60',
  }
  return map[s] || 'bg-gray-50 text-gray-600'
}

function getStatusDotClass(s: string): string {
  const map: Record<string, string> = {
    ready: 'bg-emerald-400',
    uploading: 'bg-amber-400 animate-pulse',
    embedding: 'bg-indigo-400 animate-pulse',
    pending: 'bg-gray-400',
    processing: 'bg-blue-400 animate-pulse',
    failed: 'bg-red-400',
  }
  return map[s] || 'bg-gray-400'
}

async function fetchBases() {
  loading.value = true
  try {
    const res = await listKnowledgeBases(kbPage.value, kbPageSize.value)
    bases.value = res.data.data.items
    kbTotal.value = res.data.data.total
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

async function fetchDocuments() {
  if (!selectedKb.value) return
  docLoading.value = true
  try {
    const res = await listDocuments(selectedKb.value.id, docPage.value, docPageSize.value)
    documents.value = res.data.data.items
    docTotal.value = res.data.data.total
  } catch (e) {
    console.error(e)
  } finally {
    docLoading.value = false
  }
}

async function selectKb(kb: KnowledgeBaseItem) {
  // 先用列表数据快速展示
  selectedKb.value = kb
  docPage.value = 1
  fetchDocuments()
  // 再获取完整权限信息
  try {
    const res = await getKnowledgeBase(kb.id)
    const detail = res.data.data
    if (selectedKb.value?.id === detail.id) {
      selectedKb.value = { ...selectedKb.value, ...detail }
    }
  } catch (e) {
    console.error('Failed to fetch KB detail:', e)
  }
}

async function handleCreateKb() {
  if (!newKbName.value.trim()) return
  try {
    await createKnowledgeBase({
      name: newKbName.value.trim(),
      description: newKbDesc.value.trim() || undefined,
      chat_provider: newKbChatProvider.value || undefined,
      chat_model: newKbChatModel.value.trim() || undefined,
    })
    showToast('success', '知识库已创建')
    showCreateModal.value = false
    newKbName.value = ''
    newKbDesc.value = ''
    newKbChatProvider.value = ''
    newKbChatModel.value = ''
    fetchBases()
  } catch (err: unknown) {
    showToast('error', extractErrorMessage(err, '创建失败'))
  }
}

function startRename(kb: KnowledgeBaseItem) {
  renamingKb.value = kb
  renameName.value = kb.name
}

async function handleRename() {
  if (!renamingKb.value || !renameName.value.trim()) return
  try {
    await renameKnowledgeBase(renamingKb.value.id, { name: renameName.value.trim() })
    showToast('success', '已重命名')
    renamingKb.value = null
    fetchBases()
  } catch (err: unknown) {
    showToast('error', extractErrorMessage(err, '重命名失败'))
  }
}

async function handleDeleteKb(kb: KnowledgeBaseItem) {
  if (!confirm(`确定要删除知识库 "${kb.name}" 吗？所有文档将一并删除。`)) return
  try {
    await deleteKnowledgeBase(kb.id)
    showToast('success', '知识库已删除')
    if (selectedKb.value?.id === kb.id) {
      selectedKb.value = null
      documents.value = []
    }
    fetchBases()
  } catch (err: unknown) {
    showToast('error', extractErrorMessage(err, '删除失败'))
  }
}

async function handleUpload(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file || !selectedKb.value) return
  try {
    await uploadDocument(selectedKb.value.id, file)
    showToast('success', '文档已上传，正在后台向量化...')
    fetchDocuments()
    startPolling()
  } catch (err: unknown) {
    showToast('error', extractErrorMessage(err, '上传失败'))
  } finally {
    input.value = ''
  }
}

function startPolling() {
  if (pollTimer) return
  pollTimer = setInterval(async () => {
    if (!selectedKb.value) { stopPolling(); return }
    await fetchDocuments()
    const hasPending = documents.value.some(d => d.upload_status === 'uploading' || d.upload_status === 'embedding' || d.upload_status === 'pending')
    if (!hasPending) stopPolling()
  }, 2000)
}

function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

async function handleDeleteDoc(doc: KnowledgeDocument) {
  if (!confirm(`确定要删除文档 "${doc.filename}" 吗？`)) return
  try {
    await deleteDocument(doc.id)
    showToast('success', '文档已删除')
    if (documents.value.length === 1 && docPage.value > 1) {
      docPage.value--
    }
    fetchDocuments()
  } catch (e: unknown) {
    showToast('error', extractErrorMessage(e, '删除文档失败'))
  }
}

async function handlePreview(doc: KnowledgeDocument) {
  previewDoc.value = doc
  previewLoading.value = true
  previewFullscreen.value = false
  previewData.value = null
  previewError.value = null
  try {
    const res = await previewDocument(doc.id)
    previewData.value = res.data.data
  } catch (e: any) {
    previewData.value = null
    previewError.value = e?.response?.data?.detail?.message || e?.message || '预览失败'
  } finally {
    previewLoading.value = false
  }
}

// ── 分享相关函数 ──

async function fetchShareCodes() {
  if (!sharePanelKb.value) return
  shareCodesLoading.value = true
  try {
    const res = await listShareCodes(sharePanelKb.value.id)
    shareCodes.value = res.data.data
  } catch (e) {
    console.error(e)
  } finally {
    shareCodesLoading.value = false
  }
}

async function handleGenerateCode() {
  if (!sharePanelKb.value) return
  generatingCode.value = true
  try {
    await generateShareCode(sharePanelKb.value.id, sharePermission.value)
    showToast('success', '分享码已生成')
    fetchShareCodes()
  } catch (err: unknown) {
    showToast('error', extractErrorMessage(err, '生成分享码失败'))
  } finally {
    generatingCode.value = false
  }
}

async function handleRevokeCode(code: ShareCode) {
  if (!confirm(`确定要吊销分享码 ${code.share_code} 吗？吊销后将无法再使用。`)) return
  try {
    await revokeShareCode(code.id)
    showToast('success', '分享码已吊销')
    fetchShareCodes()
  } catch (err: unknown) {
    showToast('error', extractErrorMessage(err, '吊销失败'))
  }
}

function copyShareCode(code: string) {
  navigator.clipboard.writeText(code).then(() => {
    showToast('success', '分享码已复制到剪贴板')
  }).catch(() => {
    showToast('error', '复制失败，请手动复制')
  })
}

function formatExpiry(iso: string): string {
  const d = new Date(iso)
  const now = new Date()
  const diffMs = d.getTime() - now.getTime()
  const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24))
  if (diffDays <= 0) return '已过期'
  if (diffDays === 1) return '明天'
  if (diffDays < 30) return `${diffDays} 天后`
  return `${Math.floor(diffDays / 30)} 个月后`
}

function openAccessLogs() {
  if (!sharePanelKb.value) return
  accessLogsKb.value = sharePanelKb.value
  showAccessLogs.value = true
  accessLogsPage.value = 1
  fetchAccessLogs()
}

async function fetchAccessLogs() {
  if (!accessLogsKb.value) return
  accessLogsLoading.value = true
  try {
    const res = await listAccessLogs(accessLogsKb.value.id, accessLogsPage.value)
    accessLogs.value = res.data.data.items
    accessLogsTotal.value = res.data.data.total
  } catch (e) {
    console.error(e)
  } finally {
    accessLogsLoading.value = false
  }
}

function actionText(action: string): string {
  const map: Record<string, string> = {
    view: '查看',
    query: '问答',
    download: '下载',
    share: '分享',
  }
  return map[action] || action
}

// ── 成员管理函数 ──

const filteredUsers = computed(() => {
  if (!memberSearchQuery.value) return allUsers.value
  const query = memberSearchQuery.value.toLowerCase()
  return allUsers.value.filter(u =>
    u.email.toLowerCase().includes(query) ||
    (u.display_name && u.display_name.toLowerCase().includes(query))
  )
})

const canAddMember = computed(() => {
  return addMemberUserId.value || (memberSearchQuery.value && isValidEmail(memberSearchQuery.value))
})

function isValidEmail(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
}

function onMemberSearchInput() {
  addMemberUserId.value = null
  addMemberEmail.value = null
}

function selectMemberUser(user: { id: string; email: string; display_name: string | null }) {
  addMemberUserId.value = user.id
  addMemberEmail.value = user.email
  memberSearchQuery.value = user.email
  showMemberDropdown.value = false
}

function closeMemberDropdown() {
  setTimeout(() => { showMemberDropdown.value = false }, 200)
}

async function fetchMembers() {
  if (!sharePanelKb.value) return
  membersLoading.value = true
  try {
    const res = await listKnowledgeBaseMembers(sharePanelKb.value.id)
    members.value = res.data.data
  } catch (e) {
    console.error(e)
  } finally {
    membersLoading.value = false
  }
}

async function fetchAllUsers() {
  try {
        const res = await listAllUsers()
    allUsers.value = res.data.data.items || []
  } catch (e) {
    console.error(e)
  }
}

async function handleAddMember() {
  if (!sharePanelKb.value) return
  addingMember.value = true
  try {
    const data: { user_id?: string; email?: string; permission: string } = {
      permission: addMemberPermission.value,
    }
    if (addMemberUserId.value) {
      data.user_id = addMemberUserId.value
    } else if (memberSearchQuery.value) {
      data.email = memberSearchQuery.value
    }
    
    await addKnowledgeBaseMember(sharePanelKb.value.id, data)
    showToast('success', '成员已添加')
    showAddMemberDialog.value = false
    memberSearchQuery.value = ''
    addMemberUserId.value = null
    addMemberEmail.value = null
    addMemberPermission.value = 'read'
    fetchMembers()
  } catch (err: unknown) {
    showToast('error', extractErrorMessage(err, '添加成员失败'))
  } finally {
    addingMember.value = false
  }
}

async function handleRemoveMember(member: KnowledgeBaseMember) {
  if (!sharePanelKb.value) return
  if (!confirm(`确定要移除成员 "${member.display_name || member.email}" 吗？`)) return
  try {
    await removeKnowledgeBaseMember(sharePanelKb.value.id, member.user_id)
    showToast('success', '成员已移除')
    fetchMembers()
  } catch (err: unknown) {
    showToast('error', extractErrorMessage(err, '移除成员失败'))
  }
}

async function handleUpdatePermission(userId: string, permission: string) {
  if (!sharePanelKb.value) return
  try {
    await updateKnowledgeBaseMemberPermission(sharePanelKb.value.id, userId, { permission })
    showToast('success', '权限已更新')
    fetchMembers()
  } catch (err: unknown) {
    showToast('error', extractErrorMessage(err, '更新权限失败'))
    fetchMembers()
  }
}

function openSharePanel() {
  if (!selectedKb.value) return
  sharePanelKb.value = selectedKb.value
  showSharePanel.value = true
  fetchShareCodes()
  fetchMembers()
  fetchAllUsers()
}

onMounted(() => {
  fetchBases()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped>
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.2s ease;
}
.modal-enter-active .relative,
.modal-leave-active .relative {
  transition: transform 0.2s ease, opacity 0.2s ease;
}
.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}
.modal-enter-from .relative {
  transform: scale(0.95) translateY(10px);
  opacity: 0;
}
.modal-leave-to .relative {
  transform: scale(0.95) translateY(10px);
  opacity: 0;
}

.toast-enter-active {
  transition: all 0.3s cubic-bezier(0.21, 1.02, 0.73, 1);
}
.toast-leave-active {
  transition: all 0.15s ease;
}
.toast-enter-from {
  opacity: 0;
  transform: translateX(30px) scale(0.95);
}
.toast-leave-to {
  opacity: 0;
  transform: translateX(30px) scale(0.95);
}
</style>
