# 开发排期：按天拆解

> 版本：1.0  
> 日期：2026-05-06  
> 总工期：60 个工作日（12 周）  
> 前置文档：requirement.md、spec.md、api.md、test.md

---

## 阶段一：后端 API 基础（第 1-10 天）

> 目标：后端能跑起来，能注册、登录、发消息、拿到 LLM 回复

### 第 1 天：项目脚手架

| 任务 | 产出 |
|------|------|
| 创建新目录结构（api/、models/、services/、middleware/） | 目录骨架 |
| 编写 `config.py`（pydantic-settings 读取 .env） | 配置管理 |
| 编写 `database.py`（SQLAlchemy 引擎 + Session） | 数据库连接 |
| 编写 `main.py`（FastAPI app 实例 + CORS + 路由挂载） | 可启动的空服务 |
| 验证：`uvicorn main:app` 能启动，访问 `/docs` 看到 Swagger | ✅ |

### 第 2 天：数据库模型

| 任务 | 产出 |
|------|------|
| 编写 `models/user.py`（User 表：id、email、password_hash、role、is_active、created_at） | ORM 模型 |
| 编写 `models/conversation.py`（Conversation 表：id、user_id、title、knowledge_base_id） | ORM 模型 |
| 编写 `models/message.py`（Message 表：id、conversation_id、role、content、tool_calls、token_count） | ORM 模型 |
| 编写 `models/knowledge_base.py`（KnowledgeBase 表：id、name、description、owner_id） | ORM 模型 |
| 编写 `models/document.py`（Document 表：id、knowledge_base_id、filename、status、vectorized） | ORM 模型 |
| 编写 `models/__init__.py`（导出所有模型 + Base） | 统一入口 |
| 验证：启动时自动建表，用 psql 确认表结构 | ✅ |

### 第 3 天：认证服务

| 任务 | 产出 |
|------|------|
| 编写 `services/auth_service.py` | |
| — register(email, password) → User | 注册逻辑（bcrypt 哈希） |
| — login(email, password) → Token | 登录逻辑（验证 + 签发 JWT） |
| — verify_token(token) → User | Token 解析 |
| — change_password(user_id, old, new) | 改密码 |
| 编写 `middleware/auth.py`（FastAPI Depends：从 Header 提取 Token → 解析 → 注入 current_user） | 认证中间件 |
| 验证：用 curl 测试注册和登录，拿到 Token | ✅ |

### 第 4 天：认证接口

| 任务 | 产出 |
|------|------|
| 编写 `api/auth.py` | |
| — POST /api/auth/register | 注册接口 |
| — POST /api/auth/login | 登录接口 |
| — GET /api/auth/me | 当前用户信息 |
| — PUT /api/auth/password | 修改密码 |
| 编写请求/响应 Pydantic Schema（`api/schemas/auth.py`） | 数据校验 |
| 验证：Swagger 中测试全部 4 个接口 | ✅ |

### 第 5 天：对话服务

| 任务 | 产出 |
|------|------|
| 编写 `services/chat_service.py` | |
| — create_conversation(user_id, title, kb_id) → Conversation | 创建对话 |
| — list_conversations(user_id, page, size) → List | 对话列表 |
| — get_conversation(user_id, conv_id) → Conversation | 对话详情（含消息） |
| — delete_conversation(user_id, conv_id) | 删除对话（权限校验） |
| — save_message(conv_id, role, content, tool_calls) → Message | 保存消息 |
| — get_history(conv_id) → List[Message] | 获取历史 |
| 验证：写个测试脚本，调用 service 层方法，确认数据库读写正确 | ✅ |

### 第 6 天：对话接口 + 核心引擎改造

| 任务 | 产出 |
|------|------|
| 编写 `api/chat.py` | |
| — POST /api/chat/conversations | 创建对话 |
| — GET /api/chat/conversations | 对话列表 |
| — GET /api/chat/conversations/{id} | 对话详情 |
| — DELETE /api/chat/conversations/{id} | 删除对话 |
| 改造 `core/agent.py` | |
| — 去掉 cli.py 的依赖 | |
| — 新增 `process_message(user_message, conversation_id, kb_id, on_chunk)` 方法 | 可被 API 调用 |
| — 内部调用 history（改为从 DB 读写）+ LLM + tools | 核心编排 |
| 验证：Swagger 中创建对话 → 发消息 → 拿到 LLM 回复（非流式） | ✅ |

### 第 7 天：SSE 流式输出

| 任务 | 产出 |
|------|------|
| 实现 `POST /api/chat/conversations/{id}/messages`（SSE 端点） | |
| — 使用 `StreamingResponse(media_type="text/event-stream")` | |
| — 逐 chunk 推送：`data: {"type":"chunk","content":"你"}\n\n` | |
| — 工具调用事件：`data: {"type":"tool_call","tool":"get_weather","status":"running"}\n\n` | |
| — 结束事件：`data: {"type":"done","message_id":"xxx"}\n\n` | |
| 改造 `llm/client.py` 的 `on_chunk` 回调，适配 SSE 事件格式 | 流式兼容 |
| 验证：用 EventSource 浏览器测试，看到逐字输出 | ✅ |

### 第 8 天：知识库服务

| 任务 | 产出 |
|------|------|
| 编写 `services/knowledge_service.py` | |
| — create_kb(name, desc, user_id) → KnowledgeBase | 创建知识库 |
| — list_kbs(user_id, page, size) → List | 知识库列表 |
| — delete_kb(user_id, kb_id) | 删除知识库（级联删除文档） |
| — upload_document(kb_id, file) → Document | 上传文档（保存文件 + 创建记录） |
| — list_documents(kb_id) → List | 文档列表 |
| — delete_document(doc_id) | 删除文档 |
| — check_permission(user_id, kb_id) → bool | 权限检查 |
| 编写 `services/knowledge_service.py` 中的文件校验逻辑 | |
| — 允许类型：.pdf、.docx、.txt、.md | |
| — 最大 50MB | |
| — 安全文件名（防路径遍历） | |
| 验证：上传一个 PDF，确认文件保存到 uploads/ 目录，数据库有记录 | ✅ |

### 第 9 天：知识库接口

| 任务 | 产出 |
|------|------|
| 编写 `api/knowledge.py` | |
| — POST /api/kb | 创建知识库 |
| — GET /api/kb | 知识库列表 |
| — DELETE /api/kb/{id} | 删除知识库 |
| — POST /api/kb/{id}/documents | 上传文档（multipart/form-data） |
| — GET /api/kb/{id}/documents | 文档列表 |
| — DELETE /api/kb/documents/{doc_id} | 删除文档 |
| 编写 Pydantic Schema（`api/schemas/knowledge.py`） | 数据校验 |
| 验证：Swagger 中测试知识库 CRUD + 文件上传 | ✅ |

### 第 10 天：AnythingLLM 集成 + 联调

| 任务 | 产出 |
|------|------|
| 改造 `services/knowledge_service.py` | |
| — upload_document 成功后调用 AnythingLLM API 上传文档 | 向量化触发 |
| — 新增 `query_kb(kb_id, query) → str`（调用 AnythingLLM 检索） | 知识库问答 |
| 改造 `core/agent.py` | |
| — 当对话关联了知识库时，自动调用 `query_kb` 作为上下文 | RAG 集成 |
| 全链路联调：注册 → 登录 → 创建知识库 → 上传文档 → 创建对话（关联 KB） → 发消息 → LLM 引用知识库内容回答 | ✅ |
| 产出：后端 API 全部可用，Swagger 中可完成完整流程 | 🎯 |

---

## 阶段二：前端界面（第 11-28 天）

> 目标：用户可以通过浏览器完成注册、登录、聊天、管理

### 第 11 天：前端项目初始化

| 任务 | 产出 |
|------|------|
| `npm create vite@latest frontend -- --template vue` | 项目骨架 |
| 安装依赖：element-plus、axios、pinia、vue-router | 依赖就绪 |
| 配置 vite.config.js（代理 /api → localhost:8000） | 开发代理 |
| 编写目录结构：views/、components/、stores/、api/、router/ | 目录骨架 |
| 编写 `api/request.js`（axios 实例 + 拦截器：自动带 Token、401 跳登录） | HTTP 客户端 |

### 第 12 天：登录/注册页面

| 任务 | 产出 |
|------|------|
| 编写 `views/Login.vue` | |
| — 邮箱 + 密码表单 | |
| — 登录/注册切换 | |
| — 表单校验（邮箱格式、密码长度） | |
| 编写 `stores/auth.js`（Pinia：login、register、logout、token 管理） | 状态管理 |
| 编写 `router/index.js`（路由守卫：未登录跳 /login） | 路由守卫 |
| 验证：能注册 → 自动登录 → 跳转到主页 | ✅ |

### 第 13 天：聊天界面骨架

| 任务 | 产出 |
|------|------|
| 编写 `views/Chat.vue`（主布局） | |
| — 左侧：对话列表侧边栏 | |
| — 右侧：消息区域 + 底部输入框 | |
| 编写 `components/ChatSidebar.vue` | |
| — 对话列表（时间倒序） | |
| — 新建对话按钮 | |
| — 点击切换对话 | |
| 编写 `components/MessageList.vue` | |
| — 消息气泡（用户右、助手左） | |
| — Markdown 渲染（markdown-it） | |
| 验证：页面布局正确，能显示静态消息 | ✅ |

### 第 14 天：对话功能

| 任务 | 产出 |
|------|------|
| 编写 `stores/chat.js`（Pinia：conversations、currentConversation、messages） | 状态管理 |
| 编写 `api/chat.js`（调用后端对话接口） | API 封装 |
| 实现：新建对话 → 自动加入列表 → 自动选中 | 新建流程 |
| 实现：切换对话 → 加载历史消息 | 切换流程 |
| 实现：删除对话（二次确认） | 删除流程 |
| 验证：新建 → 切换 → 删除，数据库同步正确 | ✅ |

### 第 15 天：消息收发

| 任务 | 产出 |
|------|------|
| 实现发送消息：输入框回车 → POST /api/chat/conversations/{id}/messages | 发送 |
| 实现 SSE 接收：EventSource 监听 → 逐字追加到消息气泡 | 流式显示 |
| 实现消息列表自动滚动到底部 | 体验优化 |
| 处理长文本：Markdown 实时渲染（打字过程中也能正确显示） | 渲染 |
| 验证：输入问题 → 看到 AI 逐字回复 → Markdown 标题/列表/代码块正确渲染 | ✅ |

### 第 16 天：工具调用可视化

| 任务 | 产出 |
|------|------|
| 解析 SSE 中的 `tool_call` 事件 | 事件处理 |
| 编写 `components/ToolCallCard.vue` | |
| — 折叠卡片：「🔧 正在查询天气...」 | |
| — 展开显示：工具名 + 参数 + 返回结果 | |
| — 状态图标：⏳ 运行中 / ✅ 完成 / ❌ 失败 | |
| 集成到 MessageList 中（工具调用卡片插入在消息之间） | UI 集成 |
| 验证：问天气 → 看到工具调用卡片展开/收起 | ✅ |

### 第 17 天：知识库选择 + 侧边栏优化

| 任务 | 产出 |
|------|------|
| 编写 `components/KnowledgeBaseSelect.vue` | |
| — 下拉选择知识库 | |
| — 创建对话时可选关联 KB | |
| 优化 ChatSidebar： | |
| — 对话标题显示 | |
| — 搜索对话 | |
| — 空状态引导 | |
| 验证：选择知识库创建对话 → 提问 → AI 引用知识库内容回答 | ✅ |

### 第 18 天：管理后台骨架

| 任务 | 产出 |
|------|------|
| 编写 `views/Admin.vue`（管理后台布局） | |
| — 顶部导航：用户管理 / 知识库管理 / 系统设置 | |
| — 侧边菜单 | |
| 编写 `router/index.js` 添加管理路由（/admin/*） | 路由 |
| 权限控制：非 admin 用户访问 /admin 跳回首页 | 守卫 |
| 验证：admin 登录能看到管理后台，普通用户看不到 | ✅ |

### 第 19 天：用户管理页面

| 任务 | 产出 |
|------|------|
| 编写 `views/AdminUsers.vue` | |
| — 用户列表表格（邮箱、角色、状态、注册时间） | |
| — 搜索框 | |
| — 分页 | |
| — 启用/禁用开关 | |
| — 修改角色 | |
| 编写 `api/admin.js`（管理员接口封装） | API |
| 后端补充：`api/admin.py`（GET /api/admin/users、PUT /api/admin/users/{id}） | 管理接口 |
| 验证：管理员可查看用户列表、禁用用户 | ✅ |

### 第 20 天：知识库管理页面

| 任务 | 产出 |
|------|------|
| 编写 `views/AdminKnowledge.vue` | |
| — 知识库列表（名称、文档数、创建时间） | |
| — 创建知识库对话框 | |
| — 进入知识库 → 文档列表 | |
| — 上传文档（拖拽上传 + 文件选择） | |
| — 文档状态显示（处理中/已完成/失败） | |
| — 删除文档 | |
| 验证：创建 KB → 上传 PDF → 状态变为已完成 | ✅ |

### 第 21 天：系统设置页面

| 任务 | 产出 |
|------|------|
| 编写 `views/AdminSettings.vue` | |
| — LLM 配置（API 地址、模型名、密钥，密钥脱敏显示） | |
| — AnythingLLM 配置 | |
| — 测试连接按钮 | |
| 后端补充：`api/admin.py` | |
| — GET /api/admin/settings | 读取配置 |
| — PUT /api/admin/settings | 更新配置 |
| — POST /api/admin/settings/test | 测试连接 |
| 验证：修改 LLM 地址 → 测试连接 → 对话使用新地址 | ✅ |

### 第 22-23 天：前端联调 + Bug 修复

| 任务 | 产出 |
|------|------|
| 全流程联调：注册 → 登录 → 新建对话 → 选 KB → 聊天 → 查看工具调用 | |
| 修复联调中发现的 Bug | |
| 边界情况处理：空列表、网络错误、Token 过期自动跳转 | |
| 加载状态：按钮 loading、骨架屏、空状态 | |
| 验证：完整流程无报错 | ✅ |

### 第 24-25 天：UI 打磨

| 任务 | 产出 |
|------|------|
| 响应式适配（移动端侧边栏收起/展开） | 移动端 |
| 深色模式（CSS 变量切换） | 主题 |
| 消息气泡样式优化（代码块高亮、表格渲染） | 样式 |
| 过渡动画（页面切换、消息出现） | 动效 |
| 验证：桌面端 + 移动端均可正常使用 | ✅ |

### 第 26-27 天：前端单元测试

| 任务 | 产出 |
|------|------|
| 安装 vitest + @vue/test-utils | 测试环境 |
| 测试 stores/auth.js（登录状态管理） | 测试用例 |
| 测试 stores/chat.js（对话管理逻辑） | 测试用例 |
| 测试 components/MessageList.vue（消息渲染） | 测试用例 |
| 测试 api/request.js（拦截器逻辑） | 测试用例 |
| 验证：`npm run test` 全部通过 | ✅ |

### 第 28 天：前端收尾

| 任务 | 产出 |
|------|------|
| 修复剩余 Bug | |
| 性能优化（懒加载路由、图片压缩） | |
| 代码审查 + 重构 | |
| 产出：前端全部完成，可独立运行 | 🎯 |

---

## 阶段三：权限与多用户（第 29-36 天）

> 目标：完善的权限控制、会话隔离、使用统计

### 第 29 天：数据库迁移工具

| 任务 | 产出 |
|------|------|
| 初始化 Alembic：`alembic init migrations` | 迁移框架 |
| 生成初始迁移：`alembic revision --autogenerate -m "init"` | 基线迁移 |
| 编写后续迁移脚本（添加字段、索引等） | 迁移历史 |
| 验证：`alembic upgrade head` 能正确建表 | ✅ |

### 第 30 天：知识库权限

| 任务 | 产出 |
|------|------|
| 新增 `models/kb_permission.py`（KnowledgeBasePermission 表：kb_id、user_id） | 权限模型 |
| 改造 `services/knowledge_service.py` | |
| — list_kbs：普通用户只返回有权限的知识库 | 权限过滤 |
| — check_permission：检查用户是否有权限 | 权限校验 |
| — grant_permission / revoke_permission | 权限管理 |
| 编写 `api/admin.py` 接口 | |
| — POST /api/admin/kb/{id}/permissions | 授权 |
| — DELETE /api/admin/kb/{id}/permissions/{user_id} | 撤权 |
| 验证：A 用户看不到 B 的私有知识库 | ✅ |

### 第 31 天：会话隔离加固

| 任务 | 产出 |
|------|------|
| 审查所有对话接口的权限校验 | |
| — 确保每个接口都校验 user_id == conversation.owner_id | |
| — 确保删除对话时级联清理相关数据 | |
| 审查知识库接口的权限校验 | |
| 编写权限测试用例（`tests/integration/test_permissions.py`） | 测试 |
| 验证：用户 A 无法通过 API 访问用户 B 的任何数据 | ✅ |

### 第 32 天：使用统计

| 任务 | 产出 |
|------|------|
| 新增 `models/usage_stat.py`（每日统计表：date、user_id、message_count、token_count） | 统计模型 |
| 编写 `services/stats_service.py` | |
| — record_usage(user_id, token_count) | 记录使用量 |
| — get_daily_stats(date_range) → List | 每日统计 |
| — get_user_stats(user_id) → Dict | 用户统计 |
| — get_overview() → Dict | 总览（总用户、总对话、总消息） |
| 改造 `core/agent.py`：每次 LLM 调用后记录 token 用量 | 埋点 |
| 验证：对话后统计表有记录 | ✅ |

### 第 33 天：统计接口 + 页面

| 任务 | 产出 |
|------|------|
| 编写 `api/admin.py` 统计接口 | |
| — GET /api/admin/stats/overview | 总览数据 |
| — GET /api/admin/stats/daily?start=&end= | 每日趋势 |
| — GET /api/admin/stats/users | 用户排行 |
| 编写 `views/AdminStats.vue` | |
| — 总览卡片（总用户、总对话、今日活跃） | |
| — 折线图（每日对话趋势） | 图表 |
| — 用户使用排行 | 排行 |
| 验证：管理后台能看到统计数据 | ✅ |

### 第 34 天：操作日志

| 任务 | 产出 |
|------|------|
| 新增 `models/audit_log.py`（操作日志表：user_id、action、target_type、target_id、detail、created_at） | 日志模型 |
| 编写 `middleware/audit.py`（记录管理员操作的中间件） | 自动记录 |
| 编写 `api/admin.py` 接口：GET /api/admin/audit-logs | 查询日志 |
| 编写 `views/AdminAuditLog.vue`（操作日志列表） | 日志页面 |
| 验证：管理员操作后日志表有记录，页面可查看 | ✅ |

### 第 35 天：对话重命名 + 导出

| 任务 | 产出 |
|------|------|
| 后端：PUT /api/chat/conversations/{id}（更新标题） | 重命名接口 |
| 后端：GET /api/chat/conversations/{id}/export?format=md | 导出接口 |
| 前端：对话标题双击编辑 | 交互 |
| 前端：对话右键菜单 → 导出 Markdown | 导出功能 |
| 验证：重命名后刷新页面标题不变；导出的 MD 文件内容正确 | ✅ |

### 第 36 天：阶段三联调

| 任务 | 产出 |
|------|------|
| 全流程回归测试 | |
| 权限场景覆盖验证 | |
| 统计数据准确性验证 | |
| 产出：多用户权限系统完成 | 🎯 |

---

## 阶段四：部署打包（第 37-42 天）

> 目标：Docker 一键启动，客户拿到就能用

### 第 37 天：后端 Dockerfile

| 任务 | 产出 |
|------|------|
| 编写 `Dockerfile`（Python 3.11 + pip install + uvicorn） | 后端镜像 |
| 编写 `.dockerignore` | 构建优化 |
| 本地测试：`docker build -t llm-agent-backend .` | 镜像构建 |
| 本地测试：`docker run` 启动后端 | 容器运行 |

### 第 38 天：前端 Dockerfile + Nginx

| 任务 | 产出 |
|------|------|
| 编写 `Dockerfile.frontend`（Node 构建 + Nginx 部署） | 前端镜像 |
| 编写 `nginx.conf`（静态文件 + /api 反向代理到后端） | Nginx 配置 |
| 本地测试：`docker build -t llm-agent-frontend .` | 镜像构建 |

### 第 39 天：docker-compose

| 任务 | 产出 |
|------|------|
| 编写 `docker-compose.yml` | |
| — app（后端）：端口 8000，依赖 db | |
| — frontend（前端）：端口 80，依赖 app | |
| — db（PostgreSQL 15）：端口 5432，数据卷 pgdata | |
| 编写 `.env.example`（环境变量模板） | 配置模板 |
| 编写 `init.sql`（初始化数据库和用户） | 数据库初始化 |
| 验证：`docker-compose up -d` 一键启动，浏览器访问正常 | ✅ |

### 第 40 天：数据持久化 + 健康检查

| 任务 | 产出 |
|------|------|
| 配置 volumes：pgdata、uploads、logs | 持久化 |
| 添加 healthcheck（后端 /api/health、数据库 pg_isready） | 健康检查 |
| 编写 `/api/health` 接口（检查 DB + LLM + AnythingLLM 连接状态） | 健康接口 |
| 测试：重启容器后数据不丢失 | ✅ |

### 第 41 天：部署文档

| 任务 | 产出 |
|------|------|
| 编写 `docs/deploy.md` | |
| — 环境要求（Docker 20+、Docker Compose 2+） | |
| — 快速开始（3 步启动） | |
| — 配置说明（每个环境变量的含义） | |
| — 常见问题（端口冲突、数据库连接失败等） | |
| — 备份与恢复 | |
| 编写 `README.md`（项目介绍 + 快速开始 + 文档链接） | 项目主页 |

### 第 42 天：部署阶段收尾

| 任务 | 产出 |
|------|------|
| 在一台干净的 Linux 服务器上测试部署 | 环境验证 |
| 修复部署中发现的问题 | |
| 产出：可交付的 Docker 部署包 | 🎯 |

---

## 阶段五：测试与上线（第 43-52 天）

> 目标：全面测试、修复 Bug、准备上线

### 第 43-44 天：集成测试

| 任务 | 产出 |
|------|------|
| 编写 `tests/integration/test_auth_flow.py`（注册→登录→Token 验证） | 测试用例 |
| 编写 `tests/integration/test_chat_flow.py`（创建对话→发消息→流式回复） | 测试用例 |
| 编写 `tests/integration/test_kb_flow.py`（创建 KB→上传文档→问答） | 测试用例 |
| 编写 `tests/integration/test_permissions.py`（权限隔离验证） | 测试用例 |
| 运行全部测试，修复失败用例 | ✅ |

### 第 45-46 天：安全测试

| 任务 | 产出 |
|------|------|
| 运行 `tests/security/` 全部安全测试用例 | 安全基线 |
| 路径遍历测试（../..etc/passwd） | |
| JWT 伪造/过期测试 | |
| 文件上传恶意文件测试 | |
| SQL 注入测试 | |
| XSS 注入测试（消息内容中注入脚本） | |
| 修复发现的安全问题 | ✅ |

### 第 47-48 天：性能测试

| 任务 | 产出 |
|------|------|
| 编写性能测试脚本（locust 或 ab） | 测试脚本 |
| 测试 50 并发用户同时聊天 | 并发测试 |
| 测试大文件上传（50MB PDF） | 上传测试 |
| 测试大量对话列表查询（1000+ 对话分页） | 查询性能 |
| 根据瓶颈做优化（加索引、缓存等） | ✅ |

### 第 49-50 天：Bug 修复

| 任务 | 产出 |
|------|------|
| 汇总所有测试中发现的 Bug | Bug 列表 |
| 按优先级排序修复 | |
| 回归验证已修复的 Bug | ✅ |

### 第 51-52 天：上线准备

| 任务 | 产出 |
|------|------|
| 生产环境配置审查（密钥、CORS、日志级别） | 配置审查 |
| 数据库备份脚本 | 运维脚本 |
| 最终全流程验收测试 | ✅ |
| 产出：系统可上线 | 🎯 |

---

## 阶段六：收尾与交付（第 53-60 天）

> 目标：文档完善、代码整理、交付

### 第 53-54 天：API 文档更新

| 任务 | 产出 |
|------|------|
| 根据实际实现更新 api.md | 最终 API 文档 |
| 确保 Swagger UI（/docs）与 api.md 一致 | 文档同步 |

### 第 55-56 天：用户手册

| 任务 | 产出 |
|------|------|
| 编写 `docs/user-guide.md`（普通用户使用手册） | 用户文档 |
| — 注册登录 | |
| — 创建对话、选择知识库 | |
| — 聊天功能说明 | |
| 编写 `docs/admin-guide.md`（管理员使用手册） | 管理文档 |
| — 用户管理 | |
| — 知识库管理（上传文档、权限设置） | |
| — 系统配置 | |
| — 使用统计查看 | |

### 第 57-58 天：代码整理

| 任务 | 产出 |
|------|------|
| 代码格式化（black + isort） | 代码风格 |
| 删除无用代码和注释 | 代码清洁 |
| 补充关键函数的 docstring | 可读性 |
| 更新 requirements.txt（锁定版本号） | 依赖锁定 |

### 第 59-60 天：最终交付

| 任务 | 产出 |
|------|------|
| 全量回归测试 | 最终验证 |
| 打包交付物（Docker 镜像 + 文档 + 配置模板） | 交付包 |
| 编写交付清单 | 交付文档 |
| 产出：项目完成 ✅ | 🎯 |

---

## 每日产出速查表

| 天 | 核心产出 | 验收标准 |
|----|---------|---------|
| 1 | 项目骨架 + 可启动的空服务 | uvicorn 启动，/docs 可访问 |
| 2 | 6 张数据库表 | 自动建表，psql 可查 |
| 3 | 认证服务（注册/登录/Token） | curl 测试通过 |
| 4 | 4 个认证 API 接口 | Swagger 测试通过 |
| 5 | 对话服务（CRUD） | 测试脚本通过 |
| 6 | 对话 API + agent 改造 | Swagger 发消息拿到回复 |
| 7 | SSE 流式输出 | 浏览器逐字显示 |
| 8 | 知识库服务 | 上传 PDF 成功 |
| 9 | 知识库 API | Swagger 测试通过 |
| 10 | AnythingLLM 集成 | 全链路联调通过 |
| 11 | 前端项目骨架 | npm run dev 启动 |
| 12 | 登录/注册页面 | 能注册登录 |
| 13 | 聊天界面骨架 | 布局正确 |
| 14 | 对话管理功能 | 新建/切换/删除 |
| 15 | 消息收发 + 流式显示 | 能聊天 |
| 16 | 工具调用可视化 | 看到工具卡片 |
| 17 | 知识库选择 | 选 KB 提问 |
| 18 | 管理后台骨架 | admin 可访问 |
| 19 | 用户管理页面 | 禁用/启用用户 |
| 20 | 知识库管理页面 | 上传文档 |
| 21 | 系统设置页面 | 配置 LLM |
| 22-23 | 前端联调 | 全流程无报错 |
| 24-25 | UI 打磨 | 移动端 + 深色模式 |
| 26-27 | 前端测试 | 测试全通过 |
| 28 | 前端收尾 | 前端完成 |
| 29 | Alembic 迁移 | 迁移正常 |
| 30 | 知识库权限 | 权限隔离 |
| 31 | 会话隔离加固 | 安全审查通过 |
| 32 | 使用统计服务 | 统计有数据 |
| 33 | 统计页面 | 图表显示 |
| 34 | 操作日志 | 日志可查 |
| 35 | 重命名 + 导出 | 功能可用 |
| 36 | 阶段三联调 | 回归通过 |
| 37 | 后端 Dockerfile | 镜像构建成功 |
| 38 | 前端 Dockerfile | 镜像构建成功 |
| 39 | docker-compose | 一键启动 |
| 40 | 持久化 + 健康检查 | 重启不丢数据 |
| 41 | 部署文档 | 文档完整 |
| 42 | 部署收尾 | 干净服务器验证 |
| 43-44 | 集成测试 | 测试全通过 |
| 45-46 | 安全测试 | 无高危漏洞 |
| 47-48 | 性能测试 | 50 并发通过 |
| 49-50 | Bug 修复 | Bug 清零 |
| 51-52 | 上线准备 | 验收通过 |
| 53-54 | API 文档更新 | 文档同步 |
| 55-56 | 用户手册 | 文档完整 |
| 57-58 | 代码整理 | 代码清洁 |
| 59-60 | 最终交付 | 交付完成 🎉 |
