# 测试文档：企业知识库问答系统

> 版本：1.0  
> 日期：2026-05-06  
> 状态：初稿

---

## 1. 测试策略

### 1.1 测试层次

```
┌─────────────────────────────────┐
│  E2E 测试（端到端）              │  ← Playwright / Cypress
│  模拟真实用户操作全流程           │
├─────────────────────────────────┤
│  集成测试                        │  ← httpx + pytest
│  接口联调、数据库交互             │
├─────────────────────────────────┤
│  单元测试                        │  ← pytest
│  业务逻辑、工具函数、模型验证     │
└─────────────────────────────────┘
```

### 1.2 测试工具

| 工具 | 用途 |
|------|------|
| pytest | 测试框架 |
| pytest-asyncio | 异步测试支持 |
| httpx | HTTP 客户端，用于集成测试 |
| factory-boy | 测试数据工厂 |
| pytest-cov | 覆盖率统计 |
| faker | 生成假数据 |

### 1.3 测试数据库

- 使用独立的测试数据库 `llm_agent_test`
- 每次测试前自动重建表结构
- 测试结束后清理测试数据

---

## 2. 单元测试

### 2.1 认证模块 `tests/unit/test_auth_service.py`

| 编号 | 测试用例 | 输入 | 预期输出 |
|------|---------|------|---------|
| UT-AUTH-01 | 正常注册 | 合法 email + password | 返回 user 对象，密码已哈希 |
| UT-AUTH-02 | 重复邮箱注册 | 已存在的 email | 抛出 DuplicateEmailError |
| UT-AUTH-03 | 密码强度不足 | "123" | 抛出 ValidationError |
| UT-AUTH-04 | 正确密码登录 | 正确 email + password | 返回 JWT Token |
| UT-AUTH-05 | 错误密码登录 | 正确 email + 错误 password | 抛出 InvalidCredentialsError |
| UT-AUTH-06 | 禁用账号登录 | is_active=false 的账号 | 抛出 AccountDisabledError |
| UT-AUTH-07 | Token 生成 | user_id + role | 返回有效 JWT，含正确 payload |
| UT-AUTH-08 | Token 解析 | 有效 JWT | 返回 user_id 和 role |
| UT-AUTH-09 | 过期 Token 解析 | 过期 JWT | 抛出 TokenExpiredError |
| UT-AUTH-10 | 无效 Token 解析 | 伪造 JWT | 抛出 InvalidTokenError |

```python
# 示例
def test_register_success(auth_service):
    user = auth_service.register("test@example.com", "SecurePass123")
    assert user.email == "test@example.com"
    assert user.password_hash != "SecurePass123"  # 密码已哈希
    assert user.role == "user"

def test_register_duplicate_email(auth_service, existing_user):
    with pytest.raises(DuplicateEmailError):
        auth_service.register(existing_user.email, "SecurePass123")
```

### 2.2 对话模块 `tests/unit/test_chat_service.py`

| 编号 | 测试用例 | 输入 | 预期输出 |
|------|---------|------|---------|
| UT-CHAT-01 | 创建对话 | user_id + title | 返回新对话对象 |
| UT-CHAT-02 | 获取对话列表 | user_id + 分页参数 | 返回该用户的对话列表 |
| UT-CHAT-03 | 对话隔离 | user_a 的对话 | user_b 无法访问 |
| UT-CHAT-04 | 删除对话 | conversation_id | 对话及所有消息被删除 |
| UT-CHAT-05 | 删除他人对话 | user_b 的 conversation_id | 抛出 ForbiddenError |
| UT-CHAT-06 | 保存用户消息 | conversation_id + content | Message 记录 role=user |
| UT-CHAT-07 | 保存助手消息 | conversation_id + response | Message 记录 role=assistant |
| UT-CHAT-08 | 工具调用记录 | tool_calls 数据 | Message.tool_calls 正确存储 |

### 2.3 知识库模块 `tests/unit/test_knowledge_service.py`

| 编号 | 测试用例 | 输入 | 预期输出 |
|------|---------|------|---------|
| UT-KB-01 | 创建知识库 | name + description | 返回知识库对象 |
| UT-KB-02 | 文件类型校验 | .exe 文件 | 抛出 UnsupportedFileTypeError |
| UT-KB-03 | 文件大小校验 | >50MB 文件 | 抛出 FileTooLargeError |
| UT-KB-04 | 文件保存 | 合法文件 | 文件保存到 upload_dir/{kb_id}/ |
| UT-KB-05 | 删除文档 | doc_id | 文件和记录被删除 |
| UT-KB-06 | 删除知识库 | kb_id | 知识库、文档、文件全部删除 |
| UT-KB-07 | 权限检查-有权限 | user_id + kb_id | 返回 True |
| UT-KB-08 | 权限检查-无权限 | 未授权 user_id | 返回 False |
| UT-KB-09 | 管理员跳过权限检查 | admin 角色 | 任何知识库均可访问 |

### 2.4 工具函数测试 `tests/unit/test_tools.py`

| 编号 | 测试用例 | 输入 | 预期输出 |
|------|---------|------|---------|
| UT-TOOL-01 | list_files 正常 | 合法目录路径 | 返回文件列表字符串 |
| UT-TOOL-02 | list_files 路径遍历 | "../../etc/passwd" | 返回路径验证错误 |
| UT-TOOL-03 | read_file 正常 | 合法文件路径 | 返回文件内容 |
| UT-TOOL-04 | read_file 不存在 | 不存在的路径 | 返回错误信息 |
| UT-TOOL-05 | create_file 正常 | 路径 + 内容 | 文件创建成功 |
| UT-TOOL-06 | create_file 路径遍历 | "../../evil.txt" | 返回路径验证错误 |
| UT-TOOL-07 | delete_file 正常 | 合法文件路径 | 文件被删除 |
| UT-TOOL-08 | rename_file 正常 | 旧名 + 新名 | 文件重命名成功 |
| UT-TOOL-09 | search_file_content | 目录 + 关键词 | 返回匹配结果 |
| UT-TOOL-10 | curl 正常请求 | 合法 URL | 返回响应内容 |
| UT-TOOL-11 | curl SSRF 防护 | http://169.254.169.254 | 返回安全拒绝 |
| UT-TOOL-12 | get_weather 正常 | "成都" | 返回天气信息 |
| UT-TOOL-13 | list_available_skills | 无参数 | 返回技能列表 JSON |
| UT-TOOL-14 | load_skill_content | 合法技能名 | 返回技能内容 |
| UT-TOOL-15 | load_skill_content 不存在 | "不存在的技能" | 返回错误 JSON |

### 2.5 LLM 客户端测试 `tests/unit/test_llm_client.py`

| 编号 | 测试用例 | 输入 | 预期输出 |
|------|---------|------|---------|
| UT-LLM-01 | 正常调用 | messages 列表 | 返回完整响应文本 |
| UT-LLM-02 | 流式调用 | messages + on_chunk | on_chunk 被多次调用 |
| UT-LLM-03 | 调用失败重试 | 模拟网络错误 | 自动重试 3 次 |
| UT-LLM-04 | strip_tool_call_tags | 含标签文本 | 标签被正确移除 |
| UT-LLM-05 | strip_tool_call_tags 无标签 | 纯文本 | 文本不变 |

### 2.6 历史管理测试 `tests/unit/test_history.py`

| 编号 | 测试用例 | 输入 | 预期输出 |
|------|---------|------|---------|
| UT-HIST-01 | 添加消息 | user + assistant | 列表长度 +2 |
| UT-HIST-02 | 清空历史 | 有历史数据 | 列表为空 |
| UT-HIST-03 | 计算上下文长度 | 已知消息 | 返回正确字符数 |
| UT-HIST-04 | 触发压缩-轮次 | 20 轮对话 | should_summarize=True |
| UT-HIST-05 | 触发压缩-长度 | >30000 字符 | should_summarize=True |
| UT-HIST-06 | 不触发压缩 | 5 轮对话 | should_summarize=False |
| UT-HIST-07 | build_messages | system + history | 消息格式正确 |

### 2.7 提示词测试 `tests/unit/test_prompts.py`

| 编号 | 测试用例 | 输入 | 预期输出 |
|------|---------|------|---------|
| UT-PROMPT-01 | 无技能时的系统提示词 | 无技能 | 提示词不含 skill_reference |
| UT-PROMPT-02 | 有技能时的系统提示词 | 有技能内容 | 提示词包含 skill_reference |
| UT-PROMPT-03 | 缓存机制 | 连续两次调用 | 第二次返回缓存 |
| UT-PROMPT-04 | 缓存失效 | invalidate 后调用 | 重新生成提示词 |
| UT-PROMPT-05 | 总结提示词 | 无参数 | 返回总结专用提示词 |

---

## 3. 集成测试

### 3.1 认证接口 `tests/integration/test_auth_api.py`

| 编号 | 测试用例 | 请求 | 预期响应 |
|------|---------|------|---------|
| IT-AUTH-01 | 注册成功 | POST /api/auth/register | 201, 返回 user + token |
| IT-AUTH-02 | 注册-邮箱已存在 | POST /api/auth/register | 409, code=40901 |
| IT-AUTH-03 | 注册-参数缺失 | POST /api/auth/register (无 email) | 400, code=40001 |
| IT-AUTH-04 | 登录成功 | POST /api/auth/login | 200, 返回 token |
| IT-AUTH-05 | 登录-密码错误 | POST /api/auth/login | 401, code=40101 |
| IT-AUTH-06 | 获取用户信息 | GET /api/auth/me | 200, 返回用户信息 |
| IT-AUTH-07 | 未认证访问 | GET /api/auth/me (无 Token) | 401, code=40101 |
| IT-AUTH-08 | 修改密码 | PUT /api/auth/password | 200, 密码已更新 |
| IT-AUTH-09 | 修改密码-旧密码错误 | PUT /api/auth/password | 401, code=40101 |

### 3.2 对话接口 `tests/integration/test_chat_api.py`

| 编号 | 测试用例 | 请求 | 预期响应 |
|------|---------|------|---------|
| IT-CHAT-01 | 创建对话 | POST /api/chat/conversations | 201, 返回对话对象 |
| IT-CHAT-02 | 获取对话列表 | GET /api/chat/conversations | 200, 分页列表 |
| IT-CHAT-03 | 获取对话详情 | GET /api/chat/conversations/{id} | 200, 含消息列表 |
| IT-CHAT-04 | 对话不存在 | GET /api/chat/conversations/{不存在的id} | 404, code=40401 |
| IT-CHAT-05 | 删除对话 | DELETE /api/chat/conversations/{id} | 200 |
| IT-CHAT-06 | 删除他人对话 | DELETE /api/chat/conversations/{他人的id} | 403, code=40301 |
| IT-CHAT-07 | 重命名对话 | PUT /api/chat/conversations/{id} | 200, 标题已更新 |
| IT-CHAT-08 | 发送消息-流式 | POST /api/chat/conversations/{id}/messages | 200, SSE 流 |
| IT-CHAT-09 | 发送消息-空内容 | POST .../messages (空 content) | 400, code=40001 |

### 3.3 知识库接口 `tests/integration/test_knowledge_api.py`

| 编号 | 测试用例 | 请求 | 预期响应 |
|------|---------|------|---------|
| IT-KB-01 | 创建知识库 | POST /api/knowledge/bases | 201 |
| IT-KB-02 | 普通用户创建知识库 | POST /api/knowledge/bases | 403, code=40301 |
| IT-KB-03 | 获取知识库列表 | GET /api/knowledge/bases | 200, 分页列表 |
| IT-KB-04 | 上传文档-PDF | POST .../documents (PDF 文件) | 201, status=processing |
| IT-KB-05 | 上传文档-类型不支持 | POST .../documents (.exe) | 422, code=42201 |
| IT-KB-06 | 上传文档-超大文件 | POST .../documents (>50MB) | 413, code=41301 |
| IT-KB-07 | 获取文档列表 | GET .../documents | 200 |
| IT-KB-08 | 删除文档 | DELETE .../documents/{doc_id} | 200 |
| IT-KB-09 | 删除知识库 | DELETE /api/knowledge/bases/{id} | 200 |
| IT-KB-10 | 文档预览 | GET .../documents/{doc_id}/preview | 200 |

### 3.4 管理接口 `tests/integration/test_admin_api.py`

| 编号 | 测试用例 | 请求 | 预期响应 |
|------|---------|------|---------|
| IT-ADMIN-01 | 获取用户列表 | GET /api/admin/users | 200 |
| IT-ADMIN-02 | 普通用户访问管理接口 | GET /api/admin/users | 403, code=40301 |
| IT-ADMIN-03 | 禁用用户 | PUT /api/admin/users/{id}/status | 200 |
| IT-ADMIN-04 | 修改角色 | PUT /api/admin/users/{id}/role | 200 |
| IT-ADMIN-05 | 获取配置 | GET /api/admin/config | 200, API Key 已脱敏 |
| IT-ADMIN-06 | 更新配置 | PUT /api/admin/config | 200 |
| IT-ADMIN-07 | 健康检查 | GET /api/admin/health | 200 |
| IT-ADMIN-08 | 使用统计 | GET /api/admin/stats | 200 |
| IT-ADMIN-09 | 知识库授权 | POST /api/admin/knowledge/{id}/permissions | 200 |
| IT-ADMIN-10 | 撤销授权 | DELETE /api/admin/knowledge/{id}/permissions/{user_id} | 200 |

---

## 4. SSE 流式输出测试

### 4.1 `tests/integration/test_sse_stream.py`

| 编号 | 测试用例 | 场景 | 预期行为 |
|------|---------|------|---------|
| SSE-01 | 正常流式输出 | 普通对话 | 收到 start → chunks → done |
| SSE-02 | 工具调用流式输出 | 触发天气查询 | 收到 tool_call → tool_result → chunks → done |
| SSE-03 | 多次工具调用 | 连续调用多个工具 | 每个工具调用都有 tool_call + tool_result |
| SSE-04 | LLM 服务不可用 | LLM 返回 500 | 收到 error 事件 |
| SSE-05 | 客户端断开 | 客户端提前关闭连接 | 服务端正常清理资源 |
| SSE-06 | 并发流式请求 | 同一用户多个 SSE 连接 | 每个连接独立处理 |

```python
# 示例
async def test_sse_normal_output(client, auth_headers, conversation):
    response = await client.post(
        f"/api/chat/conversations/{conversation.id}/messages",
        json={"content": "你好"},
        headers=auth_headers,
    )
    assert response.status_code == 200

    events = parse_sse_events(response.text)
    assert events[0]["type"] == "start"
    assert events[-1]["type"] == "done"
    assert any(e["type"] == "chunk" for e in events)
```

---

## 5. 安全测试

### 5.1 `tests/security/test_security.py`

| 编号 | 测试用例 | 攻击方式 | 预期结果 |
|------|---------|---------|---------|
| SEC-01 | SQL 注入 | email 字段注入 `' OR 1=1 --` | 注册失败，无 SQL 执行 |
| SEC-02 | 路径遍历-文件读取 | directory 参数 `../../etc/passwd` | 返回路径验证错误 |
| SEC-03 | 路径遍历-文件创建 | 路径 `../../evil.txt` | 返回路径验证错误 |
| SEC-04 | SSRF 攻击 | curl URL `http://169.254.169.254` | 返回安全拒绝 |
| SEC-05 | JWT 伪造 | 伪造 JWT Token | 返回 401 |
| SEC-06 | JWT 过期 | 使用过期 Token | 返回 401, code=40102 |
| SEC-07 | 权限提升 | 普通用户调用管理员接口 | 返回 403 |
| SEC-08 | 越权访问对话 | 访问他人的对话 | 返回 403 |
| SEC-09 | 文件类型绕过 | 上传 `.pdf.exe` 双扩展名 | 按实际 MIME 类型校验 |
| SEC-10 | 密码暴力破解 | 连续错误登录 | 触发限流，返回 429 |
| SEC-11 | XSS 攻击 | 消息内容含 `<script>` | 内容被转义存储 |
| SEC-12 | 大文件 DoS | 上传超大文件 | 上传前校验大小，拒绝 |

---

## 6. 性能测试

### 6.1 `tests/performance/test_performance.py`

| 编号 | 测试用例 | 并发数 | 预期指标 |
|------|---------|--------|---------|
| PERF-01 | 并发登录 | 50 | 平均响应 < 500ms |
| PERF-02 | 并发创建对话 | 50 | 平均响应 < 200ms |
| PERF-03 | 并发发送消息 | 20 | 平均首 Token < 1s |
| PERF-04 | 并发文件上传 | 10 | 单文件上传 < 5s（5MB） |
| PERF-05 | 数据库查询-对话列表 | 50 | 平均响应 < 100ms |
| PERF-06 | 数据库查询-消息历史 | 50 | 平均响应 < 200ms |

---

## 7. 测试数据工厂

### 7.1 `tests/factories.py`

```python
import factory
from llm_agent.models.user import User
from llm_agent.models.conversation import Conversation
from llm_agent.models.message import Message
from llm_agent.models.knowledge_base import KnowledgeBase
from llm_agent.models.document import Document

class UserFactory(factory.Factory):
    class Meta:
        model = User
    email = factory.Sequence(lambda n: f"user{n}@example.com")
    display_name = factory.LazyAttribute(lambda o: o.email.split("@")[0])
    password_hash = factory.LazyFunction(lambda: hash_password("TestPass123"))
    role = "user"
    is_active = True

class AdminFactory(UserFactory):
    role = "admin"

class ConversationFactory(factory.Factory):
    class Meta:
        model = Conversation
    user_id = factory.SubFactory(UserFactory)
    title = factory.Sequence(lambda n: f"对话 {n}")

class MessageFactory(factory.Factory):
    class Meta:
        model = Message
    conversation_id = factory.SubFactory(ConversationFactory)
    role = "user"
    content = factory.Sequence(lambda n: f"测试消息 {n}")

class KnowledgeBaseFactory(factory.Factory):
    class Meta:
        model = KnowledgeBase
    name = factory.Sequence(lambda n: f"知识库 {n}")
    description = factory.LazyAttribute(lambda o: f"{o.name} 的描述")
    anythingllm_slug = factory.Sequence(lambda n: f"kb-{n}")

class DocumentFactory(factory.Factory):
    class Meta:
        model = Document
    knowledge_base_id = factory.SubFactory(KnowledgeBaseFactory)
    filename = factory.Sequence(lambda n: f"doc_{n}.pdf")
    file_path = factory.Sequence(lambda n: f"/uploads/doc_{n}.pdf")
    file_size = 1024
    file_type = "application/pdf"
    status = "ready"
```

---

## 8. 测试运行

### 8.1 运行命令

```bash
# 运行所有测试
pytest

# 只运行单元测试
pytest tests/unit/

# 只运行集成测试
pytest tests/integration/

# 只运行安全测试
pytest tests/security/

# 运行指定测试文件
pytest tests/unit/test_auth_service.py

# 运行指定测试用例
pytest tests/unit/test_auth_service.py::test_register_success

# 显示详细输出
pytest -v

# 生成覆盖率报告
pytest --cov=llm_agent --cov-report=html

# 只运行失败的测试
pytest --lf
```

### 8.2 覆盖率目标

| 模块 | 目标覆盖率 |
|------|-----------|
| services/ | ≥ 90% |
| models/ | ≥ 85% |
| middleware/ | ≥ 80% |
| api/ | ≥ 75% |
| core/（改造部分） | ≥ 80% |
| tools/（现有代码） | ≥ 70% |
| **整体** | **≥ 80%** |

### 8.3 CI 集成

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15-alpine
        env:
          POSTGRES_DB: llm_agent_test
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
        ports:
          - 5432:5432
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pip install pytest pytest-cov
      - run: pytest --cov=llm_agent --cov-report=xml
        env:
          DATABASE_URL: postgresql://test:test@localhost:5432/llm_agent_test
          JWT_SECRET: test-secret
      - uses: codecov/codecov-action@v4
```

---

## 9. 测试目录结构

```
tests/
├── __init__.py
├── conftest.py                    # 全局 fixtures（数据库、客户端、认证）
├── factories.py                   # 测试数据工厂
│
├── unit/
│   ├── __init__.py
│   ├── test_auth_service.py       # 认证服务单元测试
│   ├── test_chat_service.py       # 对话服务单元测试
│   ├── test_knowledge_service.py  # 知识库服务单元测试
│   ├── test_tools.py              # 工具函数单元测试
│   ├── test_llm_client.py         # LLM 客户端单元测试
│   ├── test_history.py            # 历史管理单元测试
│   └── test_prompts.py            # 提示词单元测试
│
├── integration/
│   ├── __init__.py
│   ├── test_auth_api.py           # 认证接口集成测试
│   ├── test_chat_api.py           # 对话接口集成测试
│   ├── test_knowledge_api.py      # 知识库接口集成测试
│   ├── test_admin_api.py          # 管理接口集成测试
│   └── test_sse_stream.py         # SSE 流式输出测试
│
├── security/
│   ├── __init__.py
│   └── test_security.py           # 安全测试
│
└── performance/
    ├── __init__.py
    └── test_performance.py        # 性能测试
```

---

## 10. 测试用例统计

| 类别 | 数量 |
|------|------|
| 单元测试 | 52 |
| 集成测试 | 39 |
| SSE 测试 | 6 |
| 安全测试 | 12 |
| 性能测试 | 6 |
| **合计** | **115** |
