# API 接口文档：企业知识库问答系统

> 版本：1.0  
> 日期：2026-05-06  
> Base URL：`http://localhost:8000/api`

---

## 1. 全局约定

### 1.1 认证方式

除 `/auth/login` 和 `/auth/register` 外，所有接口需要在 Header 中携带 JWT Token：

```
Authorization: Bearer <access_token>
```

### 1.2 响应格式

**成功响应**：

```json
{
  "code": 0,
  "message": "success",
  "data": { ... }
}
```

**错误响应**：

```json
{
  "code": 40001,
  "message": "Invalid credentials",
  "data": null
}
```

**分页响应**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [...],
    "total": 100,
    "page": 1,
    "page_size": 20
  }
}
```

### 1.3 错误码

| 错误码 | HTTP 状态码 | 说明 |
|--------|------------|------|
| 0 | 200 | 成功 |
| 40001 | 400 | 请求参数错误 |
| 40101 | 401 | 未认证（Token 缺失或无效） |
| 40102 | 401 | Token 已过期 |
| 40301 | 403 | 无权限（普通用户访问管理员接口） |
| 40401 | 404 | 资源不存在 |
| 40901 | 409 | 资源冲突（如邮箱已注册） |
| 41301 | 413 | 文件过大 |
| 42201 | 422 | 文件类型不支持 |
| 50001 | 500 | 服务器内部错误 |
| 50201 | 502 | LLM 服务不可用 |
| 50202 | 502 | AnythingLLM 服务不可用 |

---

## 2. 认证模块 `/api/auth`

### 2.1 用户注册

```
POST /api/auth/register
```

**请求体**：

```json
{
  "email": "user@example.com",
  "password": "securePassword123",
  "display_name": "张三"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| email | string | ✅ | 邮箱地址 |
| password | string | ✅ | 密码，至少 8 位 |
| display_name | string | ❌ | 显示名称，默认取邮箱前缀 |

**成功响应**（201）：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "user": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "email": "user@example.com",
      "display_name": "张三",
      "role": "user",
      "created_at": "2026-05-06T19:00:00"
    },
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer"
  }
}
```

**错误响应**：

| 场景 | 错误码 | message |
|------|--------|---------|
| 邮箱已注册 | 40901 | Email already registered |
| 参数缺失 | 40001 | Missing required field: email |

### 2.2 用户登录

```
POST /api/auth/login
```

**请求体**：

```json
{
  "email": "user@example.com",
  "password": "securePassword123"
}
```

**成功响应**（200）：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "user": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "email": "user@example.com",
      "display_name": "张三",
      "role": "user"
    },
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer"
  }
}
```

**错误响应**：

| 场景 | 错误码 | message |
|------|--------|---------|
| 邮箱或密码错误 | 40101 | Invalid credentials |
| 账号已禁用 | 40101 | Account disabled |

### 2.3 获取当前用户信息

```
GET /api/auth/me
```

**成功响应**（200）：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "display_name": "张三",
    "role": "user",
    "avatar_url": null,
    "created_at": "2026-05-06T19:00:00"
  }
}
```

### 2.4 修改密码

```
PUT /api/auth/password
```

**请求体**：

```json
{
  "old_password": "oldPassword123",
  "new_password": "newPassword456"
}
```

**成功响应**（200）：

```json
{
  "code": 0,
  "message": "Password updated successfully",
  "data": null
}
```

---

## 3. 对话模块 `/api/chat`

### 3.1 创建对话

```
POST /api/chat/conversations
```

**请求体**：

```json
{
  "title": "关于天气的咨询",
  "knowledge_base_id": "550e8400-e29b-41d4-a716-446655440001"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| title | string | ❌ | 对话标题，默认"新对话" |
| knowledge_base_id | string | ❌ | 关联的知识库 ID |

**成功响应**（201）：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440010",
    "title": "关于天气的咨询",
    "knowledge_base_id": "550e8400-e29b-41d4-a716-446655440001",
    "created_at": "2026-05-06T19:00:00",
    "updated_at": "2026-05-06T19:00:00"
  }
}
```

### 3.2 获取对话列表

```
GET /api/chat/conversations?page=1&page_size=20
```

**查询参数**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| page | int | 1 | 页码 |
| page_size | int | 20 | 每页数量，最大 100 |

**成功响应**（200）：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440010",
        "title": "关于天气的咨询",
        "knowledge_base_id": "550e8400-e29b-41d4-a716-446655440001",
        "message_count": 6,
        "created_at": "2026-05-06T19:00:00",
        "updated_at": "2026-05-06T19:05:00"
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 20
  }
}
```

### 3.3 获取对话详情

```
GET /api/chat/conversations/{conversation_id}
```

**成功响应**（200）：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440010",
    "title": "关于天气的咨询",
    "knowledge_base_id": "550e8400-e29b-41d4-a716-446655440001",
    "created_at": "2026-05-06T19:00:00",
    "updated_at": "2026-05-06T19:05:00",
    "messages": [
      {
        "id": "msg-001",
        "role": "user",
        "content": "成都今天天气怎么样？",
        "tool_calls": null,
        "created_at": "2026-05-06T19:00:00"
      },
      {
        "id": "msg-002",
        "role": "assistant",
        "content": "成都今天天气晴朗，气温 22°C...",
        "tool_calls": [
          {
            "name": "get_weather",
            "parameters": {"city": "成都"},
            "status": "success"
          }
        ],
        "model": "qwen/qwen3.5-9b",
        "token_usage": 150,
        "latency_ms": 2300,
        "created_at": "2026-05-06T19:00:02"
      }
    ]
  }
}
```

### 3.4 发送消息（流式输出）

```
POST /api/chat/conversations/{conversation_id}/messages
Content-Type: application/json
Accept: text/event-stream
```

**请求体**：

```json
{
  "content": "成都今天天气怎么样？"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| content | string | ✅ | 用户消息内容 |

**成功响应**（200，SSE 流）：

```
data: {"type": "start", "message_id": "msg-003"}

data: {"type": "chunk", "content": "成"}
data: {"type": "chunk", "content": "都"}
data: {"type": "chunk", "content": "今天"}
data: {"type": "chunk", "content": "天气晴朗"}

data: {"type": "tool_call", "name": "get_weather", "parameters": {"city": "成都"}, "status": "running"}
data: {"type": "tool_result", "name": "get_weather", "result": "成都今天：晴，22°C，湿度 45%", "status": "success"}

data: {"type": "chunk", "content": "，气温 22°C"}
data: {"type": "chunk", "content": "，适合外出。"}

data: {"type": "done", "message_id": "msg-003", "model": "qwen/qwen3.5-9b", "token_usage": 150, "latency_ms": 2300}
```

**SSE 事件类型**：

| type | 说明 | 包含字段 |
|------|------|---------|
| `start` | 开始生成 | message_id |
| `chunk` | 文本片段 | content |
| `tool_call` | 工具调用开始 | name, parameters, status |
| `tool_result` | 工具调用结果 | name, result, status |
| `error` | 出错 | error_code, message |
| `done` | 生成完毕 | message_id, model, token_usage, latency_ms |

**错误响应**（SSE 事件）：

```
data: {"type": "error", "error_code": 50201, "message": "LLM service unavailable"}
```

### 3.5 重命名对话

```
PUT /api/chat/conversations/{conversation_id}
```

**请求体**：

```json
{
  "title": "新标题"
}
```

**成功响应**（200）：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440010",
    "title": "新标题",
    "updated_at": "2026-05-06T19:10:00"
  }
}
```

### 3.6 删除对话

```
DELETE /api/chat/conversations/{conversation_id}
```

**成功响应**（200）：

```json
{
  "code": 0,
  "message": "Conversation deleted",
  "data": null
}
```

---

## 4. 知识库模块 `/api/knowledge`

### 4.1 创建知识库

```
POST /api/knowledge/bases
```

**请求体**：

```json
{
  "name": "公司规章制度",
  "description": "包含员工手册、考勤制度、报销流程等"
}
```

**成功响应**（201）：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440020",
    "name": "公司规章制度",
    "description": "包含员工手册、考勤制度、报销流程等",
    "anythingllm_slug": "kb-550e8400",
    "document_count": 0,
    "created_at": "2026-05-06T19:00:00"
  }
}
```

### 4.2 获取知识库列表

```
GET /api/knowledge/bases?page=1&page_size=20
```

**成功响应**（200）：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440020",
        "name": "公司规章制度",
        "description": "包含员工手册、考勤制度、报销流程等",
        "document_count": 5,
        "created_at": "2026-05-06T19:00:00"
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 20
  }
}
```

### 4.3 获取知识库详情

```
GET /api/knowledge/bases/{kb_id}
```

**成功响应**（200）：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440020",
    "name": "公司规章制度",
    "description": "包含员工手册、考勤制度、报销流程等",
    "anythingllm_slug": "kb-550e8400",
    "document_count": 5,
    "created_by": "550e8400-e29b-41d4-a716-446655440000",
    "created_at": "2026-05-06T19:00:00",
    "updated_at": "2026-05-06T19:05:00"
  }
}
```

### 4.4 删除知识库

```
DELETE /api/knowledge/bases/{kb_id}
```

**成功响应**（200）：

```json
{
  "code": 0,
  "message": "Knowledge base deleted",
  "data": null
}
```

### 4.5 上传文档

```
POST /api/knowledge/bases/{kb_id}/documents
Content-Type: multipart/form-data
```

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | File | ✅ | 文件（PDF/Word/TXT/Markdown） |

**成功响应**（201）：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "doc-001",
    "filename": "员工手册.pdf",
    "file_size": 1048576,
    "file_type": "application/pdf",
    "status": "processing",
    "created_at": "2026-05-06T19:00:00"
  }
}
```

**错误响应**：

| 场景 | 错误码 | message |
|------|--------|---------|
| 文件过大 | 41301 | File too large, max 50MB |
| 类型不支持 | 42201 | Unsupported file type: .exe |

### 4.6 获取文档列表

```
GET /api/knowledge/bases/{kb_id}/documents
```

**成功响应**（200）：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "doc-001",
        "filename": "员工手册.pdf",
        "file_size": 1048576,
        "file_type": "application/pdf",
        "status": "ready",
        "error_message": null,
        "created_at": "2026-05-06T19:00:00"
      },
      {
        "id": "doc-002",
        "filename": "报销流程.docx",
        "file_size": 524288,
        "file_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "status": "processing",
        "error_message": null,
        "created_at": "2026-05-06T19:01:00"
      }
    ],
    "total": 2,
    "page": 1,
    "page_size": 20
  }
}
```

**文档状态枚举**：

| status | 说明 |
|--------|------|
| `uploading` | 上传中 |
| `processing` | 向量化处理中 |
| `ready` | 就绪，可用于检索 |
| `failed` | 处理失败 |

### 4.7 删除文档

```
DELETE /api/knowledge/bases/{kb_id}/documents/{doc_id}
```

**成功响应**（200）：

```json
{
  "code": 0,
  "message": "Document deleted",
  "data": null
}
```

### 4.8 文档预览

```
GET /api/knowledge/bases/{kb_id}/documents/{doc_id}/preview
```

**成功响应**（200）：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "doc-001",
    "filename": "员工手册.pdf",
    "content_preview": "第一章 总则\n第一条 本手册适用于...",
    "page_count": 25
  }
}
```

---

## 5. 技能模块 `/api/skills`

### 5.1 获取技能列表

```
GET /api/skills
```

**成功响应**（200）：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "name": "公文撰写",
        "description": "公文撰写技能，触发词：公文、通知、报告",
        "enabled": true
      },
      {
        "name": "数据分析",
        "description": "数据分析技能，触发词：分析、统计、报表",
        "enabled": true
      }
    ],
    "total": 2
  }
}
```

### 5.2 启用/禁用技能

```
PUT /api/skills/{skill_name}/toggle
```

**请求体**：

```json
{
  "enabled": false
}
```

**成功响应**（200）：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "name": "公文撰写",
    "enabled": false
  }
}
```

---

## 6. 管理模块 `/api/admin`

> ⚠️ 以下接口仅管理员（role=admin）可访问。

### 6.1 获取用户列表

```
GET /api/admin/users?page=1&page_size=20&search=zhang
```

**查询参数**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| page | int | 1 | 页码 |
| page_size | int | 20 | 每页数量 |
| search | string | — | 搜索关键词（匹配邮箱、显示名） |

**成功响应**（200）：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "email": "zhang@example.com",
        "display_name": "张三",
        "role": "user",
        "is_active": true,
        "conversation_count": 15,
        "created_at": "2026-05-06T19:00:00"
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 20
  }
}
```

### 6.2 禁用/启用用户

```
PUT /api/admin/users/{user_id}/status
```

**请求体**：

```json
{
  "is_active": false
}
```

**成功响应**（200）：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "is_active": false
  }
}
```

### 6.3 修改用户角色

```
PUT /api/admin/users/{user_id}/role
```

**请求体**：

```json
{
  "role": "admin"
}
```

**成功响应**（200）：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "role": "admin"
  }
}
```

### 6.4 知识库权限管理

#### 授权用户访问知识库

```
POST /api/admin/knowledge/{kb_id}/permissions
```

**请求体**：

```json
{
  "user_ids": ["user-id-1", "user-id-2"]
}
```

**成功响应**（200）：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "granted": 2,
    "knowledge_base_id": "550e8400-e29b-41d4-a716-446655440020"
  }
}
```

#### 撤销用户访问权限

```
DELETE /api/admin/knowledge/{kb_id}/permissions/{user_id}
```

**成功响应**（200）：

```json
{
  "code": 0,
  "message": "Permission revoked",
  "data": null
}
```

#### 查看知识库的授权用户

```
GET /api/admin/knowledge/{kb_id}/permissions
```

**成功响应**（200）：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "user_id": "user-id-1",
        "email": "zhang@example.com",
        "display_name": "张三",
        "granted_at": "2026-05-06T19:00:00"
      }
    ],
    "total": 1
  }
}
```

### 6.5 系统配置

#### 获取当前配置

```
GET /api/admin/config
```

**成功响应**（200）：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "llm_base_url": "http://localhost:1234/v1",
    "llm_model": "qwen/qwen3.5-9b",
    "llm_api_key_set": true,
    "anythingllm_base_url": "http://localhost:3001",
    "anythingllm_api_key_set": true,
    "anythingllm_workspace_slug": "ai-36041121"
  }
}
```

> ⚠️ API Key 只返回是否已设置（`_set` 字段），不返回实际值。

#### 更新配置

```
PUT /api/admin/config
```

**请求体**（所有字段可选，只更新传入的字段）：

```json
{
  "llm_base_url": "http://new-llm-server:1234/v1",
  "llm_model": "gpt-4o",
  "llm_api_key": "sk-new-key"
}
```

**成功响应**（200）：

```json
{
  "code": 0,
  "message": "Configuration updated",
  "data": null
}
```

### 6.6 使用统计

```
GET /api/admin/stats
```

**成功响应**（200）：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "total_users": 25,
    "active_users_today": 12,
    "total_conversations": 1580,
    "conversations_today": 45,
    "total_messages": 12640,
    "total_documents": 89,
    "total_knowledge_bases": 5,
    "total_tokens_used": 2560000
  }
}
```

### 6.7 系统健康检查

```
GET /api/admin/health
```

**成功响应**（200）：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "status": "healthy",
    "checks": {
      "database": {
        "status": "ok",
        "latency_ms": 2
      },
      "llm_service": {
        "status": "ok",
        "latency_ms": 150,
        "model": "qwen/qwen3.5-9b"
      },
      "anythingllm": {
        "status": "ok",
        "latency_ms": 80
      }
    }
  }
}
```

---

## 7. 文件上传通用约定

### 7.1 支持的文件类型

| 类型 | MIME 类型 | 扩展名 |
|------|----------|--------|
| PDF | application/pdf | .pdf |
| Word | application/vnd.openxmlformats-officedocument.wordprocessingml.document | .docx |
| 纯文本 | text/plain | .txt |
| Markdown | text/markdown | .md |

### 7.2 限制

| 限制项 | 值 |
|--------|-----|
| 单文件最大 | 50MB |
| 单次上传 | 1 个文件（批量上传 P1 阶段支持多文件） |

---

## 8. SSE 连接规范

### 8.1 客户端连接

```javascript
const eventSource = new EventSource(
  '/api/chat/conversations/' + conversationId + '/messages?content=' + encodeURIComponent(content),
  { headers: { 'Authorization': 'Bearer ' + token } }
);

// 注意：EventSource 不支持自定义 Header
// 实际实现中使用 fetch + ReadableStream 替代：
const response = await fetch(url, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer ' + token
  },
  body: JSON.stringify({ content: message })
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  const text = decoder.decode(value);
  // 解析 SSE 事件
}
```

### 8.2 服务端推送格式

```
data: {"type": "chunk", "content": "你"}

data: {"type": "chunk", "content": "好"}

data: {"type": "done", "message_id": "msg-001", "model": "qwen/qwen3.5-9b", "token_usage": 150, "latency_ms": 2300}

```

每个事件以 `\n\n`（空行）分隔。

---

## 9. 接口总览

| 模块 | 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|------|
| 认证 | POST | `/api/auth/register` | 注册 | 公开 |
| 认证 | POST | `/api/auth/login` | 登录 | 公开 |
| 认证 | GET | `/api/auth/me` | 当前用户信息 | 登录 |
| 认证 | PUT | `/api/auth/password` | 修改密码 | 登录 |
| 对话 | POST | `/api/chat/conversations` | 创建对话 | 登录 |
| 对话 | GET | `/api/chat/conversations` | 对话列表 | 登录 |
| 对话 | GET | `/api/chat/conversations/{id}` | 对话详情 | 登录 |
| 对话 | POST | `/api/chat/conversations/{id}/messages` | 发送消息（SSE） | 登录 |
| 对话 | PUT | `/api/chat/conversations/{id}` | 重命名 | 登录 |
| 对话 | DELETE | `/api/chat/conversations/{id}` | 删除对话 | 登录 |
| 知识库 | POST | `/api/knowledge/bases` | 创建知识库 | 管理员 |
| 知识库 | GET | `/api/knowledge/bases` | 知识库列表 | 登录 |
| 知识库 | GET | `/api/knowledge/bases/{id}` | 知识库详情 | 登录 |
| 知识库 | DELETE | `/api/knowledge/bases/{id}` | 删除知识库 | 管理员 |
| 文档 | POST | `/api/knowledge/bases/{id}/documents` | 上传文档 | 管理员 |
| 文档 | GET | `/api/knowledge/bases/{id}/documents` | 文档列表 | 登录 |
| 文档 | DELETE | `/api/knowledge/bases/{id}/documents/{doc_id}` | 删除文档 | 管理员 |
| 文档 | GET | `/api/knowledge/bases/{id}/documents/{doc_id}/preview` | 文档预览 | 登录 |
| 技能 | GET | `/api/skills` | 技能列表 | 登录 |
| 技能 | PUT | `/api/skills/{name}/toggle` | 启用/禁用 | 管理员 |
| 管理 | GET | `/api/admin/users` | 用户列表 | 管理员 |
| 管理 | PUT | `/api/admin/users/{id}/status` | 禁用/启用用户 | 管理员 |
| 管理 | PUT | `/api/admin/users/{id}/role` | 修改角色 | 管理员 |
| 管理 | POST | `/api/admin/knowledge/{id}/permissions` | 授权知识库 | 管理员 |
| 管理 | DELETE | `/api/admin/knowledge/{id}/permissions/{user_id}` | 撤销授权 | 管理员 |
| 管理 | GET | `/api/admin/knowledge/{id}/permissions` | 查看授权 | 管理员 |
| 管理 | GET | `/api/admin/config` | 获取配置 | 管理员 |
| 管理 | PUT | `/api/admin/config` | 更新配置 | 管理员 |
| 管理 | GET | `/api/admin/stats` | 使用统计 | 管理员 |
| 管理 | GET | `/api/admin/health` | 健康检查 | 管理员 |
