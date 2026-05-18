# 技术规格文档：LLM Agent Framework → 企业知识库问答系统

> 版本：1.0  
> 日期：2026-05-06  
> 状态：初稿

---

## 1. 系统架构

### 1.1 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                    浏览器（Vue 3）                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │ 聊天界面  │  │ 管理后台  │  │ 登录页面  │              │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘              │
│       └──────────────┼──────────────┘                    │
│                      │ HTTP / SSE                        │
└──────────────────────┼──────────────────────────────────┘
                       │
┌──────────────────────┼──────────────────────────────────┐
│                FastAPI 服务层                             │
│  ┌───────────────────┼──────────────────────────────┐   │
│  │              middleware/                          │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐            │   │
│  │  │  JWT    │ │  CORS   │ │  限流   │            │   │
│  │  └─────────┘ └─────────┘ └─────────┘            │   │
│  └───────────────────┬──────────────────────────────┘   │
│                      │                                   │
│  ┌───────────────────┼──────────────────────────────┐   │
│  │              api/ (路由层)                        │   │
│  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐  │   │
│  │  │ auth │ │ chat │ │  kb  │ │ skill│ │ admin│  │   │
│  │  └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘  │   │
│  └─────┼────────┼────────┼────────┼────────┼───────┘   │
│        │        │        │        │        │            │
│  ┌─────┼────────┼────────┼────────┼────────┼───────┐   │
│  │              services/ (业务逻辑层)              │   │
│  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐  │   │
│  │  │ auth │ │ chat │ │  kb  │ │ skill│ │ admin│  │   │
│  │  └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘  │   │
│  └─────┼────────┼────────┼────────┼────────┼───────┘   │
│        │        │        │        │        │            │
│  ┌─────┼────────┼────────┼────────┼────────┼───────┐   │
│  │              core/ (核心引擎层 - 现有代码)       │   │
│  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐           │   │
│  │  │agent │ │llm   │ │tools │ │history│           │   │
│  │  └──────┘ └──────┘ └──────┘ └──────┘           │   │
│  └─────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────┼──────────────────────────────────┐
│              外部服务                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │PostgreSQL│  │AnythingLLM│  │ LLM API  │              │
│  │ (数据库)  │  │ (向量检索) │  │ (模型推理) │              │
│  └──────────┘  └──────────┘  └──────────┘              │
└─────────────────────────────────────────────────────────┘
```

### 1.2 分层说明

| 层级 | 目录 | 职责 | 依赖 |
|------|------|------|------|
| **路由层** | `api/` | HTTP 路由定义、请求参数校验、响应格式化 | services/ |
| **业务逻辑层** | `services/` | 业务规则、权限校验、数据编排 | core/、models/ |
| **核心引擎层** | `core/`、`llm/`、`tools/` | LLM 调用、工具执行、对话管理（现有代码） | 外部服务 |
| **数据层** | `models/`、`database.py` | ORM 模型、数据库操作 | PostgreSQL |
| **中间件层** | `middleware/` | 认证、CORS、限流、日志 | — |

---

## 2. 目录结构

```
llm-agent-framework/
├── src/
│   └── llm_agent/
│       ├── __init__.py
│       ├── config.py                  # 新增：统一配置管理
│       ├── database.py                # 新增：数据库连接
│       │
│       ├── api/                       # 新增：路由层
│       │   ├── __init__.py
│       │   ├── auth.py                # 认证接口
│       │   ├── chat.py                # 对话接口
│       │   ├── knowledge.py           # 知识库接口
│       │   ├── skill.py               # 技能接口
│       │   └── admin.py               # 管理接口
│       │
│       ├── services/                  # 新增：业务逻辑层
│       │   ├── __init__.py
│       │   ├── auth_service.py        # 认证服务
│       │   ├── chat_service.py        # 对话服务
│       │   ├── knowledge_service.py   # 知识库服务
│       │   ├── skill_service.py       # 技能服务
│       │   └── admin_service.py       # 管理服务
│       │
│       ├── models/                    # 新增：数据库模型
│       │   ├── __init__.py
│       │   ├── user.py                # 用户模型
│       │   ├── conversation.py        # 对话模型
│       │   ├── message.py             # 消息模型
│       │   ├── knowledge_base.py      # 知识库模型
│       │   └── document.py            # 文档模型
│       │
│       ├── middleware/                 # 新增：中间件
│       │   ├── __init__.py
│       │   ├── auth.py                # JWT 认证中间件
│       │   └── cors.py                # CORS 配置
│       │
│       ├── core/                      # 改造：核心引擎
│       │   ├── __init__.py
│       │   ├── agent.py               # 改造：去掉 CLI 代码
│       │   ├── history.py             # 改造：支持数据库读写
│       │   └── prompts.py             # 不动
│       │
│       ├── llm/                       # 不动
│       │   ├── __init__.py
│       │   └── client.py
│       │
│       ├── tools/                     # 不动
│       │   ├── __init__.py
│       │   ├── registry.py
│       │   ├── file_tools.py
│       │   ├── network_tools.py
│       │   └── skill_tools.py
│       │
│       ├── logging/                   # 改造：增加数据库日志
│       │   ├── __init__.py
│       │   └── logger.py
│       │
│       └── cli.py                     # 废弃：保留但不再使用
│
├── frontend/                          # 新增：前端项目
│   ├── package.json
│   ├── vite.config.js
│   ├── src/
│   │   ├── App.vue
│   │   ├── main.js
│   │   ├── router/
│   │   ├── views/
│   │   │   ├── Login.vue
│   │   │   ├── Chat.vue
│   │   │   └── admin/
│   │   │       ├── Dashboard.vue
│   │   │       ├── Users.vue
│   │   │       ├── KnowledgeBase.vue
│   │   │       └── Skills.vue
│   │   ├── components/
│   │   │   ├── MessageBubble.vue
│   │   │   ├── ToolCallDisplay.vue
│   │   │   └── FileUpload.vue
│   │   ├── api/
│   │   │   └── index.js              # Axios 封装
│   │   └── stores/
│   │       ├── auth.js
│   │       └── chat.js
│   └── public/
│
├── docs/                              # 新增：文档
│   ├── requirement.md
│   ├── spec.md
│   ├── api.md
│   └── test.md
│
├── docker/
│   ├── Dockerfile                     # 新增
│   ├── Dockerfile.frontend            # 新增
│   └── docker-compose.yml             # 新增
│
├── .env                               # 改造：增加数据库配置
├── env.example                        # 改造
├── requirements.txt                   # 新增：Python 依赖
├── README.md                          # 改造
└── .gitignore                         # 改造
```

---

## 3. 数据库设计

### 3.1 ER 关系

```
User 1──N Conversation 1──N Message
User 1──N UserKnowledgeBase N──1 KnowledgeBase
KnowledgeBase 1──N Document
```

### 3.2 表结构

#### users（用户表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| email | VARCHAR(255) | UNIQUE, NOT NULL | 邮箱 |
| password_hash | VARCHAR(255) | NOT NULL | bcrypt 哈希密码 |
| display_name | VARCHAR(100) | | 显示名称 |
| role | ENUM('admin','user') | NOT NULL, DEFAULT 'user' | 角色 |
| is_active | BOOLEAN | NOT NULL, DEFAULT true | 是否启用 |
| avatar_url | VARCHAR(500) | | 头像 URL |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 更新时间 |

#### conversations（对话表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| user_id | UUID | FK → users.id, NOT NULL | 所属用户 |
| title | VARCHAR(255) | | 对话标题（用户可自定义） |
| knowledge_base_id | UUID | FK → knowledge_bases.id | 关联的知识库 |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 更新时间 |

#### messages（消息表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| conversation_id | UUID | FK → conversations.id, NOT NULL | 所属对话 |
| role | ENUM('user','assistant','system') | NOT NULL | 角色 |
| content | TEXT | NOT NULL | 消息内容 |
| tool_calls | JSONB | | 工具调用记录 |
| model | VARCHAR(100) | | 使用的模型 |
| token_usage | INTEGER | | Token 消耗 |
| latency_ms | INTEGER | | 响应延迟（毫秒） |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 创建时间 |

#### knowledge_bases（知识库表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| name | VARCHAR(255) | NOT NULL | 知识库名称 |
| description | TEXT | | 描述 |
| anythingllm_slug | VARCHAR(255) | UNIQUE | AnythingLLM 工作区 slug |
| created_by | UUID | FK → users.id | 创建者 |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 更新时间 |

#### documents（文档表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| knowledge_base_id | UUID | FK → knowledge_bases.id, NOT NULL | 所属知识库 |
| filename | VARCHAR(255) | NOT NULL | 原始文件名 |
| file_path | VARCHAR(500) | NOT NULL | 存储路径 |
| file_size | INTEGER | | 文件大小（字节） |
| file_type | VARCHAR(50) | | 文件类型 |
| status | ENUM('uploading','processing','ready','failed') | NOT NULL, DEFAULT 'uploading' | 处理状态 |
| error_message | TEXT | | 失败原因 |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 创建时间 |

#### user_knowledge_bases（用户-知识库关联表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| user_id | UUID | FK → users.id, NOT NULL | 用户 |
| knowledge_base_id | UUID | FK → knowledge_bases.id, NOT NULL | 知识库 |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 授权时间 |

**唯一约束**：`(user_id, knowledge_base_id)`

---

## 4. 核心模块改造规格

### 4.1 agent.py 改造

**现状**：`ChatClientWithSkills` 类同时负责 CLI 交互和核心编排。

**改造目标**：分离 CLI 和核心逻辑，核心逻辑变为可被 API 调用的 Service。

```python
# 改造后的核心方法签名
class ChatClientWithSkills:
    def chat(self, user_input: str, conversation_id: str = None,
             knowledge_base_id: str = None) -> dict:
        """
        非流式对话，返回完整结果。
        返回: {"response": "...", "tool_calls": [...], "model": "...", "usage": {...}}
        """

    def chat_stream(self, user_input: str, conversation_id: str = None,
                    knowledge_base_id: str = None) -> Generator[str, None, None]:
        """
        流式对话，逐块 yield。
        yield: {"type": "chunk", "content": "..."}
               {"type": "tool_call", "name": "...", "status": "running"}
               {"type": "tool_result", "name": "...", "result": "..."}
               {"type": "done", "response": "...", "usage": {...}}
        """
```

**改动点**：
1. 移除 `__init__` 中的 CLI 相关初始化
2. 移除 `stream_chat` 中的 `print()` 调用
3. 移除 `handle_tool_calls_and_respond` 中的 `print()` 调用
4. 新增 `chat()` 和 `chat_stream()` 方法，返回结构化数据
5. 保留 `parse_tool_call()`、`build_messages()` 等内部方法

### 4.2 history.py 改造

**现状**：对话历史存储在内存列表中。

**改造目标**：支持数据库持久化，同时保留内存模式（用于单用户 CLI）。

```python
class ChatHistory:
    def __init__(self, llm_caller, summary_prompt_getter, db_session=None, user_id=None):
        """
        db_session 不为 None 时，从数据库读写。
        db_session 为 None 时，使用内存列表（向后兼容）。
        """

    def load_from_db(self, conversation_id: str):
        """从数据库加载指定对话的历史"""

    def save_to_db(self, conversation_id: str):
        """将当前历史保存到数据库"""

    def list_conversations(self, user_id: str, page=1, page_size=20) -> dict:
        """列出用户的对话列表"""
```

### 4.3 新增 config.py

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # LLM
    llm_base_url: str = "http://localhost:1234/v1"
    llm_model: str = "qwen/qwen3.5-9b"
    llm_api_key: str = "EMPTY"

    # AnythingLLM
    anythingllm_api_key: str = ""
    anythingllm_workspace_slug: str = "AI"
    anythingllm_base_url: str = "http://localhost:3001"

    # Database
    database_url: str = "postgresql://user:pass@localhost:5432/llm_agent"

    # Auth
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24 小时

    # File Storage
    upload_dir: str = "./uploads"
    max_upload_size_mb: int = 50

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list = ["http://localhost:5173"]

    class Config:
        env_file = ".env"
```

### 4.4 新增 database.py

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

engine = None
SessionLocal = None

def init_database(database_url: str):
    global engine, SessionLocal
    engine = create_engine(database_url)
    SessionLocal = sessionmaker(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class Base(DeclarativeBase):
    pass
```

---

## 5. 认证流程

```
用户登录
  → POST /api/auth/login {email, password}
  → 验证密码（bcrypt）
  → 生成 JWT Token（含 user_id, role, exp）
  → 返回 {access_token, token_type, user}

后续请求
  → Header: Authorization: Bearer <token>
  → 中间件验证 Token
  → 解析 user_id, role 注入 request.state
  → 路由函数通过 request.state.user 获取当前用户
```

---

## 6. 对话流程

```
用户发送消息
  → POST /api/chat/conversations/{id}/messages {content, knowledge_base_id?}
  → ChatService 创建 Message 记录（role=user）
  → ChatService 调用 ChatClientWithSkills.chat_stream()
  → SSE 流式推送：
      data: {"type": "chunk", "content": "你"}
      data: {"type": "chunk", "content": "好"}
      data: {"type": "tool_call", "name": "get_weather", "status": "running"}
      data: {"type": "tool_result", "name": "get_weather", "result": "..."}
      data: {"type": "chunk", "content": "今天天气..."}
      data: {"type": "done", "response": "完整回复", "usage": {"tokens": 150}}
  → ChatService 创建 Message 记录（role=assistant）
  → 更新对话的 updated_at
```

---

## 7. 知识库集成流程

```
上传文档
  → POST /api/knowledge/{kb_id}/documents (multipart/form-data)
  → 校验文件类型和大小
  → 保存文件到 upload_dir/{kb_id}/
  → 创建 Document 记录（status=uploading）
  → 异步任务：
      1. 调用 AnythingLLM API 上传文档
      2. 等待向量化完成
      3. 更新 Document 状态为 ready
      4. 失败时更新为 failed，记录 error_message

对话时检索
  → 用户选择关联知识库
  → ChatService 在系统提示词中注入知识库上下文
  → LLM 通过 anythingllm_query 工具检索知识库
  → 返回基于知识库内容的回答
```

---

## 8. 技术选型

| 组件 | 选型 | 版本 | 理由 |
|------|------|------|------|
| Web 框架 | FastAPI | 0.115+ | 异步支持好，自带 OpenAPI 文档 |
| ASGI 服务器 | uvicorn | 0.34+ | FastAPI 官方推荐 |
| ORM | SQLAlchemy | 2.0+ | 成熟稳定，支持异步 |
| 数据库迁移 | Alembic | 1.15+ | SQLAlchemy 官方配套 |
| 数据库 | PostgreSQL | 15+ | JSONB 支持好，适合存储工具调用记录 |
| 认证 | PyJWT | 2.10+ | 轻量 JWT 实现 |
| 密码加密 | bcrypt | 4.3+ | 行业标准 |
| 配置管理 | pydantic-settings | 2.8+ | 类型安全的配置 |
| 前端框架 | Vue 3 | 3.5+ | 轻量、生态好 |
| UI 组件库 | Element Plus | 2.9+ | 企业级组件丰富 |
| 构建工具 | Vite | 6+ | 快速开发体验 |
| HTTP 客户端 | Axios | 1.8+ | 拦截器支持好 |
| 状态管理 | Pinia | 3+ | Vue 3 官方推荐 |
| 容器化 | Docker + Compose | — | 一键部署 |

---

## 9. 环境变量

```env
# === LLM 配置 ===
LLM_BASE_URL=http://localhost:1234/v1
LLM_MODEL=qwen/qwen3.5-9b
LLM_API_KEY=EMPTY

# === AnythingLLM 配置 ===
ANYTHINGLLM_API_KEY=your-api-key
ANYTHINGLLM_WORKSPACE_SLUG=ai-36041121
ANYTHINGLLM_BASE_URL=http://localhost:3001

# === 数据库配置 ===
DATABASE_URL=postgresql://llm_agent:password@localhost:5432/llm_agent

# === JWT 配置 ===
JWT_SECRET=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

# === 文件存储 ===
UPLOAD_DIR=./uploads
MAX_UPLOAD_SIZE_MB=50

# === 服务器配置 ===
HOST=0.0.0.0
PORT=8000
CORS_ORIGINS=["http://localhost:5173"]

# === 日志 ===
LOG_FILE_PATH=./logs
LOG_LEVEL=INFO
```

---

## 10. Python 依赖

```
# requirements.txt

# Web 框架
fastapi>=0.115.0
uvicorn[standard]>=0.34.0
python-multipart>=0.0.20

# 数据库
sqlalchemy>=2.0.0
alembic>=1.15.0
psycopg2-binary>=2.9.0

# 认证
PyJWT>=2.10.0
bcrypt>=4.3.0

# 配置
pydantic-settings>=2.8.0

# 工具
aiofiles>=24.0.0
```

---

## 11. 部署架构

```
docker-compose.yml
├── app (FastAPI 后端)
│   ├── Dockerfile
│   ├── 端口: 8000
│   └── 依赖: db, anythingllm
├── frontend (Vue 前端)
│   ├── Dockerfile.frontend
│   ├── 端口: 80 → 5173
│   └── Nginx 反向代理 API 请求到 app
├── db (PostgreSQL)
│   ├── 镜像: postgres:15-alpine
│   ├── 端口: 5432
│   └── 数据卷: pgdata
└── volumes
    ├── pgdata (数据库)
    ├── uploads (上传文件)
    └── logs (日志)
```
