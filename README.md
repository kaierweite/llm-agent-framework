# LLM Agent Framework

> 基于大语言模型的智能代理框架

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![Node.js](https://img.shields.io/badge/Node.js-18+-green.svg)](https://nodejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![Vue](https://img.shields.io/badge/Vue-3.5+-4FC08D.svg)](https://vuejs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-336791.svg)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-6+-DC382F.svg)](https://redis.io/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

功能强大的全栈智能代理框架，集成了工具调用、技能系统、知识库 RAG、部门管理和审计日志等企业级功能。提供 RESTful API 和现代化的 Vue 3 前端界面。

## 📑 目录

- [特性](#-特性)
- [架构](#-架构)
- [快速开始](#-快速开始)
- [API 文档](#-api-文档)
- [前端界面](#-前端界面)
- [工具系统](#-工具系统)
- [技能系统](#-技能系统)
- [知识库管理](#-知识库管理)
- [部门管理](#-部门管理)
- [安全机制](#-安全机制)
- [技术栈](#-技术栈)
- [项目结构](#-项目结构)
- [开发指南](#-开发指南)
- [部署](#-部署)
- [常见问题](#-常见问题)
- [贡献](#-贡献)
- [许可证](#-许可证)

## ✨ 特性

### 核心功能

- 🤖 **智能对话** - 支持多轮对话、SSE 流式输出、上下文自动压缩
- 🛠️ **工具调用** - 15+ 内置工具，支持文件操作、网络请求、天气查询等
- 📚 **知识库 RAG** - 文档上传、向量化存储、语义检索、AnythingLLM 集成
- 🎯 **技能系统** - 自定义 Markdown 技能规则，动态加载启用
- 🏢 **部门管理** - 树形组织架构、多级部门、成员权限控制
- 📊 **审计日志** - 完整操作追踪、IP 记录、请求耗时统计
- 🔐 **安全认证** - JWT 鉴权、bcrypt 加密、SSRF 防护、请求限流

### 企业级特性

- 👥 **用户管理** - 角色权限、部门关联、账号状态管理
- 🔑 **知识库分享** - 分享码机制、权限控制、访问日志
- 📈 **管理后台** - 用户/部门/知识库/审计日志/系统设置五合一
- 🔍 **历史搜索** - 对话历史关键字搜索、Redis 存储
- 📝 **文档解析** - 支持 Word、Excel、PPT、PDF 多种格式
- 🚀 **高可用** - 数据库迁移、连接池、重试机制、日志系统

## 🏗️ 架构

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Vue 3      │────▶│  FastAPI     │────▶│  PostgreSQL │
│  Frontend   │     │  Backend     │     │  Database   │
└─────────────┘     └──────────────┘     └─────────────┘
       │                   │                     │
       │                   ▼                     ▼
       │            ┌──────────────┐     ┌─────────────┐
       │            │   Redis      │     │  AnythingLLM│
       │            │   Cache      │     │  RAG        │
       │            └──────────────┘     └─────────────┘
       │                   │
       │                   ▼
       │            ┌──────────────┐
       └───────────▶│  LLM Client  │
                    │  (OpenAI)    │
                    └──────────────┘
```

## 🚀 快速开始

### 前置要求

- Python 3.12+
- Node.js 18+
- PostgreSQL 14+
- Redis 6+
- AnythingLLM（可选）

### 1. 克隆项目

```bash
git clone https://github.com/your-org/llm-agent-framework.git
cd llm-agent-framework
```

### 2. 环境配置

```bash
# 复制环境变量模板
cp env.example .env
```

编辑 `.env` 文件：

```env
# LLM 配置
LLM_BASE_URL=http://localhost:1234/v1
LLM_MODEL=qwen/qwen3.5-9b
LLM_API_KEY=EMPTY

# JWT 密钥（生产环境务必修改）
JWT_SECRET_KEY=your-secret-key-change-in-production

# 数据库配置
DATABASE_URL=postgresql://user:password@localhost:5432/llm_agent_db

# Redis 配置
REDIS_URL=redis://localhost:6379/0

# AnythingLLM（可选）
ANYTHINGLLM_API_KEY=your-anythingllm-api-key
ANYTHINGLLM_WORKSPACE_SLUG=ai

# 日志配置
LOG_FILE_PATH=./logs/chat.log
LOG_LEVEL=INFO
```

### 3. 安装依赖

```bash
# 后端依赖
pip install -r requirements.txt

# 前端依赖
cd frontend
npm install
```

### 4. 数据库初始化

```bash
# 创建数据库
psql -U postgres -c "CREATE DATABASE llm_agent_db;"

# 运行数据库迁移
cd src
alembic upgrade head

# 创建初始管理员账号（可选）
python seed.py
```

### 5. 启动服务

**终端 1 - 后端服务（端口 8000）：**

```bash
set PYTHONPATH=src
python -m uvicorn llm_agent.main:app --host 0.0.0.0 --port 8000 --reload
```

**终端 2 - 前端开发服务器（端口 5173）：**

```bash
cd frontend
npm run dev
```

访问 `http://localhost:5173` 开始使用。

### 6. 测试连接

```bash
# 测试后端 API
curl http://localhost:8000/api/health

# 预期响应
{"status": "ok", "version": "1.0.0"}
```

## 📚 API 文档

### 认证接口

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/api/auth/register` | 用户注册 | ❌ |
| POST | `/api/auth/login` | 用户登录 | ❌ |
| GET | `/api/auth/me` | 获取当前用户 | ✅ |
| PUT | `/api/auth/password` | 修改密码 | ✅ |

### 对话接口

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/api/chat/conversations` | 创建对话 | ✅ |
| GET | `/api/chat/conversations` | 对话列表 | ✅ |
| GET | `/api/chat/conversations/{id}` | 对话详情 | ✅ |
| PUT | `/api/chat/conversations/{id}` | 重命名对话 | ✅ |
| DELETE | `/api/chat/conversations/{id}` | 删除对话 | ✅ |
| POST | `/api/chat/conversations/{id}/messages` | 发送消息 | ✅ |
| POST | `/api/chat/conversations/{id}/messages/stream` | 流式消息 | ✅ |

### 知识库接口

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/api/knowledge/bases` | 创建知识库 | ✅ |
| GET | `/api/knowledge/bases` | 知识库列表 | ✅ |
| GET | `/api/knowledge/bases/{id}` | 知识库详情 | ✅ |
| PUT | `/api/knowledge/bases/{id}` | 更新知识库 | ✅ |
| DELETE | `/api/knowledge/bases/{id}` | 删除知识库 | ✅ |
| POST | `/api/knowledge/bases/{id}/documents` | 上传文档 | ✅ |
| GET | `/api/knowledge/bases/{id}/documents` | 文档列表 | ✅ |
| DELETE | `/api/knowledge/documents/{id}` | 删除文档 | ✅ |
| POST | `/api/knowledge/bases/{id}/query` | RAG 查询 | ✅ |
| POST | `/api/knowledge/bases/{id}/share-code` | 生成分享码 | ✅ |
| POST | `/api/knowledge/bases/access-by-code` | 分享码访问 | ✅ |

### 部门管理接口

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/api/departments` | 创建部门 | ✅ Admin |
| GET | `/api/departments/tree` | 部门树 | ✅ |
| GET | `/api/departments/{id}` | 部门详情 | ✅ |
| PUT | `/api/departments/{id}` | 更新部门 | ✅ Admin |
| DELETE | `/api/departments/{id}` | 删除部门 | ✅ Admin |
| POST | `/api/departments/{id}/members` | 添加成员 | ✅ Admin |
| GET | `/api/departments/{id}/members` | 成员列表 | ✅ |
| DELETE | `/api/departments/{id}/members/{user_id}` | 移除成员 | ✅ Admin |

### 管理后台接口（需 admin 角色）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/admin/users` | 用户列表 |
| PUT | `/api/admin/users/{id}/role` | 切换角色 |
| PUT | `/api/admin/users/{id}/toggle-active` | 启用/禁用 |
| POST | `/api/admin/users/{id}/reset-password` | 重置密码 |
| GET | `/api/admin/stats` | 系统统计 |
| GET | `/api/admin/settings` | 系统设置 |
| PUT | `/api/admin/settings` | 更新设置 |
| GET | `/api/admin/audit-logs` | 审计日志 |

完整的 API 文档请访问：`http://localhost:8000/docs`

## 🎨 前端界面

### 用户界面

- **登录/注册页** - JWT 鉴权，支持邮箱注册
- **主聊天页** - 实时对话、流式输出、工具调用展示
- **知识库浏览** - 独立知识库页面、文档预览
- **分享访问** - 通过分享码访问知识库
- **个人设置** - 个人信息管理、密码修改

### 管理后台（`/admin`）

- **用户管理** - 用户 CRUD、角色切换、状态管理
- **部门管理** - 树形组织架构、成员管理
- **知识库管理** - 知识库 CRUD、文档上传
- **审计日志** - 操作记录查询、行为追踪
- **系统设置** - 动态参数配置、技能管理

## 🛠️ 工具系统

内置 15+ 工具函数，AI 可自动调用：

| 工具 | 功能 | 参数 |
|------|------|------|
| `list_files` | 列出目录文件 | `directory` |
| `read_file` | 读取文件内容 | `directory`, `filename` |
| `create_file` | 创建文件 | `directory`, `filename`, `content` |
| `rename_file` | 重命名文件 | `directory`, `old_name`, `new_name` |
| `delete_file` | 删除文件 | `directory`, `filename` |
| `delete_directory` | 删除目录 | `directory`, `dirname` |
| `search_file_content` | 搜索文件内容 | `directory`, `keyword` |
| `curl_network_request` | 网络请求 | `url`, `method` |
| `get_weather` | 天气查询 | `city` |
| `search_chat_history` | 搜索历史 | `query` |
| `anythingllm_query` | AnythingLLM 查询 | `query` |
| `list_available_skills` | 技能列表 | - |
| `load_skill_content` | 加载技能 | `skill_name` |

### 工具调用示例

```python
# AI 自动调用工具完成任务
用户：帮我查看当前目录下的所有 Python 文件
AI: [调用 list_files 工具]
    [返回结果并展示]
```

## 🎯 技能系统

支持自定义技能扩展，通过 Markdown 文件定义规则。

### 技能结构

```
.agents/skills/
├── data-analyst/
│   └── SKILL.md
├── code-reviewer/
│   └── SKILL.md
└── translator/
    └── SKILL.md
```

### SKILL.md 格式

```markdown
---
name: 数据分析师
description: 专业数据分析技能。触发词：数据分析、统计、图表。
---

# 技能规则

## 核心规则
1. 使用 Python 进行数据处理
2. 优先使用 pandas 和 numpy 库
3. 生成可视化图表时使用 matplotlib

## 输出格式
- 数据分析结果以表格形式呈现
- 关键指标加粗显示
```

### 管理技能

```bash
# 查看技能列表
GET /api/admin/skills

# 创建技能
POST /api/admin/skills

# 启用/禁用技能
PUT /api/admin/skills/{id}/toggle-enabled
```

## 📚 知识库管理

### 支持的文档格式

- 📄 **Office 文档** - Word (.docx), Excel (.xlsx), PowerPoint (.pptx)
- 📄 **PDF 文档** - .pdf
- 📄 **文本文件** - .txt, .md, .csv

### 工作流程

```
1. 创建知识库
   ↓
2. 上传文档
   ↓
3. 自动解析（AnythingLLM 向量化）
   ↓
4. RAG 查询（语义检索）
   ↓
5. AI 生成答案
```

### 知识库分享

```bash
# 生成分享码
POST /api/knowledge/bases/{kb_id}/share-code
{
  "permission": "read"  // read | query
}

# 返回
{
  "share_code": "KB-ABC123",
  "expires_at": "2024-12-31T23:59:59"
}

# 通过分享码访问
POST /api/knowledge/bases/access-by-code
{
  "share_code": "KB-ABC123"
}
```

## 🏢 部门管理

### 树形结构

```
公司
├── 技术部
│   ├── 前端组
│   └── 后端组
├── 产品部
└── 运营部
```

### 权限控制

| 角色 | 权限 |
|------|------|
| 管理员 | 全部操作 |
| 部门负责人 | 管理部门成员 |
| 普通成员 | 查看部门信息 |

### 成员管理

```bash
# 添加部门成员
POST /api/departments/{id}/members
{
  "user_id": "user-123"
}

# 批量添加成员
POST /api/departments/{id}/members/batch
{
  "user_ids": ["user-1", "user-2"]
}

# 移除成员
DELETE /api/departments/{id}/members/{user_id}
```

## 🔐 安全机制

### 认证与授权

- ✅ JWT Token 认证所有 API 接口
- ✅ bcrypt 密码哈希（12 轮）
- ✅ 角色权限控制（admin/member）
- ✅ 管理员自我操作防护

### 数据安全

- ✅ 路径验证防止目录遍历
- ✅ SSRF 防护拒绝内网访问
- ✅ 请求限流防止滥用
- ✅ 审计日志记录所有操作

### 最佳实践

```env
# 生产环境必须修改
JWT_SECRET_KEY=your-secure-random-key-here
DATABASE_URL=postgresql://user:strong-password@host/db
```

## 💻 技术栈

### 后端

- **框架**: FastAPI 0.115+
- **数据库**: PostgreSQL 14+
- **ORM**: SQLAlchemy 2.0+
- **缓存**: Redis 6+
- **认证**: PyJWT + bcrypt
- **验证**: Pydantic v2
- **迁移**: Alembic
- **服务器**: Uvicorn / Gunicorn

### 前端

- **框架**: Vue 3.5+
- **语言**: TypeScript 6+
- **状态管理**: Pinia 3+
- **路由**: Vue Router 4+
- **样式**: Tailwind CSS v4
- **构建工具**: Vite 8+
- **HTTP**: Axios 1.16+

### AI 集成

- **LLM**: OpenAI 兼容 API
- **流式**: SSE (Server-Sent Events)
- **向量**: AnythingLLM / ChromaDB
- **嵌入**: Sentence Transformers

## 📁 项目结构

<details>
<summary>点击展开完整结构</summary>

```
llm-agent-framework/
├── src/llm_agent/              # Python 后端
│   ├── api/                    # API 路由层
│   │   ├── auth.py            # 认证接口
│   │   ├── chat.py            # 对话接口
│   │   ├── knowledge.py       # 知识库接口
│   │   ├── kb_share.py        # 知识库分享
│   │   ├── department.py      # 部门管理
│   │   ├── skill.py           # 技能管理
│   │   ├── admin.py           # 管理后台
│   │   └── schemas/           # Pydantic 模型
│   ├── core/                  # 核心业务
│   │   ├── agent.py           # 智能代理
│   │   ├── chat_engine.py     # 对话引擎
│   │   └── tool_executor.py   # 工具执行器
│   ├── models/                # ORM 模型
│   ├── services/              # 业务逻辑
│   ├── tools/                 # 工具系统
│   ├── middleware/            # 中间件
│   └── logging/               # 日志系统
├── frontend/                  # Vue 3 前端
│   ├── src/
│   │   ├── api/               # API 封装
│   │   ├── components/        # 组件
│   │   ├── stores/            # Pinia
│   │   ├── views/             # 页面
│   │   └── router/            # 路由
│   └── package.json
├── alembic/                   # 数据库迁移
├── .agents/skills/            # 技能定义
├── scripts/                   # 辅助脚本
├── requirements.txt           # Python 依赖
└── README.md                  # 本文档
```

</details>

## 📖 开发指南

### 添加新工具

1. 在 `src/llm_agent/tools/` 创建工具文件
2. 实现工具函数并注册
3. 更新工具文档

```python
# tools/my_tool.py
from .registry import register_tool

@register_tool
def my_tool(param1: str, param2: int):
    """工具描述"""
    # 实现逻辑
    return result
```

### 添加新技能

1. 在 `.agents/skills/` 创建技能目录
2. 编写 `SKILL.md` 文件
3. 在管理后台启用技能

### 数据库迁移

```bash
# 创建迁移脚本
alembic revision -m "add_new_column"

# 应用迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1
```

### 前端开发

```bash
cd frontend

# 开发模式
npm run dev

# 构建生产版本
npm run build

# 预览构建结果
npm run preview
```

## 🚀 部署

### 生产环境部署

#### 1. 后端部署（Gunicorn + Nginx）

```bash
# 安装 Gunicorn
pip install gunicorn

# 启动服务
gunicorn llm_agent.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 120
```

#### 2. Nginx 配置

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location / {
        proxy_pass http://localhost:5173;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

#### 3. 前端部署

```bash
cd frontend

# 构建
npm run build

# 部署 dist 目录到 Nginx
```

### Docker 部署（可选）

```dockerfile
# Dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ ./src/
EXPOSE 8000

CMD ["uvicorn", "llm_agent.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## ❓ 常见问题

### 1. 数据库连接失败

```bash
# 检查 PostgreSQL 服务
pg_isready

# 检查数据库是否存在
psql -U postgres -l | grep llm_agent_db

# 创建数据库
psql -U postgres -c "CREATE DATABASE llm_agent_db;"
```

### 2. Redis 连接失败

```bash
# 检查 Redis 服务
redis-cli ping

# 启动 Redis
redis-server
```

### 3. 前端无法连接后端

- 检查 Vite 代理配置 (`vite.config.ts`)
- 确认后端服务已启动
- 检查 CORS 设置

### 4. LLM 连接失败

```env
# 检查环境变量
LLM_BASE_URL=http://your-llm-server:1234/v1
LLM_API_KEY=your-api-key
```

## 🤝 贡献

欢迎贡献代码、报告问题或提出建议！

### 贡献流程

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

### 开发环境设置

```bash
# 克隆项目
git clone https://github.com/your-org/llm-agent-framework.git

# 安装依赖
pip install -r requirements.txt
cd frontend && npm install

# 运行测试
pytest
```

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 📞 联系方式

- 项目地址：https://github.com/your-org/llm-agent-framework
- 问题反馈：https://github.com/your-org/llm-agent-framework/issues

## 🙏 致谢

感谢以下开源项目：

- [FastAPI](https://fastapi.tiangolo.com/)
- [Vue.js](https://vuejs.org/)
- [SQLAlchemy](https://www.sqlalchemy.org/)
- [AnythingLLM](https://anythingllm.com/)

---

**Made with ❤️ by the LLM Agent Framework Team**
