# LLM Agent 功能增强方案

> 版本：1.0  
> 日期：2026-05-10  
> 状态：待开发

---

## 概述

本文档定义了 LLM Agent 项目的 6 项功能增强，按优先级排序并包含完整的技术实现方案。

### 开发顺序

| 序号 | 功能 | 工作量 | 优先级 |
|------|------|--------|--------|
| 1 | 对话全文搜索 | 小 | ⭐⭐⭐ 高 |
| 2 | 对话导出 Markdown | 小 | ⭐⭐⭐ 高 |
| 3 | 工具调用时间线可视化 | 中 | ⭐⭐ 中 |
| 4 | 消息重新生成（regenerate） | 中 | ⭐⭐ 中 |
| 5 | 消息编辑并重新发送 | 大 | ⭐ 中 |
| 6 | PDF 导出 + 分享链接 | 大 | ⭐ 低 |

---

## 功能 1：对话全文搜索

### 需求

当前前端侧边栏搜索只过滤对话标题（`title`），无法搜索消息内容。后端已有 `search_chat_history` 工具供 LLM 使用，但未暴露给前端。

### 技术方案

#### 后端

**新增 API**：`GET /api/chat/search`

```python
# 请求参数
query: str          # 搜索关键词（必填）
limit: int = 20     # 分页大小
offset: int = 0     # 偏移量

# 响应结构
{
    "total": 15,
    "items": [
        {
            "conversation_id": "uuid",
            "conversation_title": "对话标题",
            "messages": [
                {
                    "id": "msg-uuid",
                    "role": "user",
                    "content": "消息内容...",
                    "created_at": "2026-05-10T09:00:00",
                    "highlight": "...包含<b>关键词</b>的片段..."
                }
            ]
        }
    ]
}
```

**实现逻辑**：

```python
# services/chat_service.py 新增函数
def search_messages(
    db: Session,
    user_id: str,
    query: str,
    limit: int = 20,
    offset: int = 0,
) -> Tuple[list, int]:
    """全文搜索消息内容"""
    # 1. 在 messages 表中 LIKE 搜索
    # 2. 关联 conversations 表获取对话标题
    # 3. 按 conversation_id 分组
    # 4. 生成 highlight 片段
    # 5. 分页返回
```

**PostgreSQL 优化**：
- 当前阶段使用 `LIKE '%关键词%'` 即可
- 数据量超过 10 万条后可启用 `pg_trgm` 全文索引或 `tsvector`

#### 前端

**改动位置**：`ChatSidebar.vue`

**交互流程**：
1. 用户在搜索框输入关键词
2. 调用 `GET /api/chat/search?q=关键词`
3. 显示搜索结果列表（按对话分组）
4. 点击某条结果 → 跳转到对应对话 → 高亮定位到该消息

**UI 设计**：
```
搜索框
├── 对话 A（3 条匹配）
│   ├── 消息片段 1...
│   ├── 消息片段 2...
│   └── 消息片段 3...
├── 对话 B（1 条匹配）
│   └── 消息片段 1...
└── 共 15 条结果，显示 1-20
```

---

## 功能 2：对话导出 Markdown

### 需求

用户需要将对话内容导出为可离线查看的文件。

### 技术方案

#### 后端

**新增 API**：`GET /api/chat/conversations/{id}/export?format=markdown`

**实现逻辑**：

```python
# services/chat_service.py 新增函数
def export_conversation_markdown(
    db: Session,
    user_id: str,
    conversation_id: str,
) -> str:
    """导出对话为 Markdown 格式"""
    conv = get_conversation(db, user_id, conversation_id)
    messages = get_history(db, conversation_id)
    
    md = f"# {conv.title}\n\n"
    md += f"**导出时间**：{datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
    md += "---\n\n"
    
    for msg in messages:
        if msg.role == "user":
            md += "## 👤 用户\n\n"
        else:
            md += "## 🤖 助手\n\n"
        md += f"{msg.content}\n\n"
        md += "---\n\n"
    
    return md
```

**响应**：
- `Content-Type: text/markdown; charset=utf-8`
- `Content-Disposition: attachment; filename="对话标题.md"`

#### 前端

**改动位置**：对话右键菜单 / 对话操作按钮

**交互流程**：
1. 点击"导出 Markdown"按钮
2. 调用 `GET /api/chat/conversations/{id}/export?format=markdown`
3. 浏览器自动下载 `.md` 文件

---

## 功能 3：工具调用时间线可视化

### 需求

当前工具调用结果只在 `ToolCallCard` 里展示，用户看不到 Agent 的完整推理过程。需要展示：LLM 思考 → 调用工具 → 等待结果 → 继续回复 的时间线。

### 技术方案

#### 数据模型变更

**Message 模型新增字段**：

```python
# models/message.py
class Message(Base):
    # ... 现有字段 ...
    tool_calls = Column(JSON, nullable=True)  # 工具调用序列
```

**tool_calls 字段结构**：

```json
[
    {
        "id": "call-uuid",
        "name": "get_weather",
        "arguments": {"city": "北京"},
        "result": "晴，25°C",
        "status": "success",  // success | error | timeout
        "started_at": "2026-05-10T09:00:00.000",
        "completed_at": "2026-05-10T09:00:01.234",
        "duration_ms": 1234
    }
]
```

#### 后端改动

**ChatEngine 改造**：

```python
# core/chat_engine.py
def process_message(self, ...):
    tool_calls序列 = []
    
    # 工具调用开始时
    def on_tool_start(tool_call_id, name, arguments):
        tool_calls序列.append({
            "id": tool_call_id,
            "name": name,
            "arguments": arguments,
            "status": "running",
            "started_at": datetime.now().isoformat(),
        })
    
    # 工具调用结束时
    def on_tool_result(tool_call_id, result, status):
        for tc in tool_calls序列:
            if tc["id"] == tool_call_id:
                tc["result"] = result
                tc["status"] = status  # success | error | timeout
                tc["completed_at"] = datetime.now().isoformat()
                tc["duration_ms"] = 计算耗时
                break
    
    # ... 执行 LLM 调用 ...
    
    # 保存消息时写入 tool_calls
    save_message(db, conv_id, "assistant", reply, tool_calls=tool_calls序列)
```

**已有消息兼容**：
- `tool_calls` 为 `null` 的消息不显示时间线按钮
- 零迁移成本，无需处理历史数据

#### 前端改动

**ToolCallCard.vue 改造为时间线样式**：

```
🤖 助手消息内容...

▼ 🔧 推理过程（3 步，耗时 2.3s）
  ├─ ✅ get_weather（北京） → 1.2s
  │     结果：晴，25°C
  ├─ ✅ search_file_content（天气报告） → 0.8s
  │     结果：找到 3 个文件
  └─ ✅ read_file（report.md） → 0.3s
        结果：文件内容...
```

**交互设计**：
- 默认收起，点击展开
- 每个步骤显示：状态图标 + 工具名 + 参数摘要 + 耗时
- 展开后显示完整参数和结果
- 错误步骤用红色高亮

---

## 功能 4：消息重新生成（regenerate）

### 需求

用户对 AI 回答不满意时，可以重新生成最后一次回复。

### 技术方案

#### 后端

**新增 API**：`POST /api/chat/conversations/{id}/regenerate`

```python
# 请求体（可选）
{
    "message_id": "msg-uuid"  # 可选：指定从哪条用户消息重新生成
}

# 响应：SSE 流式输出（与发送消息相同）
```

**实现逻辑**：

```python
# services/chat_service.py 新增函数
def regenerate_response(
    db: Session,
    user_id: str,
    conversation_id: str,
    message_id: str | None = None,
) -> Generator[str, None, None]:
    """重新生成最后一次助手回复"""
    conv = get_conversation(db, user_id, conversation_id)
    if not conv:
        raise ChatError(404, "对话不存在")
    
    # 1. 获取消息历史
    messages = get_history(db, conversation_id)
    
    # 2. 找到最后一条 user message
    if message_id:
        # 指定消息
        target_msg = next(m for m in messages if m.id == message_id)
        target_idx = messages.index(target_msg)
    else:
        # 默认最后一条 user message
        for i in range(len(messages) - 1, -1, -1):
            if messages[i].role == "user":
                target_idx = i
                break
    
    # 3. 删除该 user message 之后的所有消息
    msg_ids_to_delete = [m.id for m in messages[target_idx + 1:]]
    delete_messages_by_ids(db, conversation_id, msg_ids_to_delete)
    
    # 4. 用最后一条 user message 重新生成
    user_message = messages[target_idx].content
    # 调用 process_message（不重复存 user message）
    # ... 
```

**关键点**：
- 不重复存储 user message
- 删除上一轮的 assistant 回复
- 重新走一遍完整的 LLM 调用流程

#### 前端

**改动位置**：`MessageList.vue` 中 assistant 消息气泡

**UI 设计**：
```
🤖 助手消息内容...
    [🔄 重新生成]  [📋 复制]
```

**交互流程**：
1. 用户点击"重新生成"按钮
2. 调用 `POST /api/chat/conversations/{id}/regenerate`
3. 流式输出新的回复，替换原有内容
4. 工具调用时间线同步更新

---

## 功能 5：消息编辑并重新发送

### 需求

用户可以编辑已发送的用户消息，然后重新发送，AI 会基于编辑后的内容重新回复。

### 技术方案

#### 后端

**新增 API**：`PUT /api/chat/conversations/{id}/messages/{msg_id}`

```python
# 请求体
{
    "content": "编辑后的内容"
}

# 响应：SSE 流式输出（与发送消息相同）
```

**实现逻辑**：

```python
# services/chat_service.py 新增函数
def edit_and_resend(
    db: Session,
    user_id: str,
    conversation_id: str,
    message_id: str,
    new_content: str,
) -> Generator[str, None, None]:
    """编辑用户消息并重新生成"""
    conv = get_conversation(db, user_id, conversation_id)
    if not conv:
        raise ChatError(404, "对话不存在")
    
    # 1. 获取消息历史
    messages = get_history(db, conversation_id)
    target_idx = next(i for i, m in enumerate(messages) if m.id == message_id)
    
    # 2. 更新用户消息内容
    messages[target_idx].content = new_content
    db.commit()
    
    # 3. 删除该消息之后的所有消息
    msg_ids_to_delete = [m.id for m in messages[target_idx + 1:]]
    delete_messages_by_ids(db, conversation_id, msg_ids_to_delete)
    
    # 4. 用编辑后的内容重新生成
    # ... 调用 process_message ...
```

#### 前端

**改动位置**：`MessageList.vue` 中 user 消息气泡

**UI 设计**：
```
👤 用户消息内容...
    [✏️ 编辑]  [📋 复制]
```

**交互流程**：
1. 用户点击"编辑"按钮
2. 消息气泡变为可编辑的 input/textarea
3. 用户修改内容，点击"保存"或按 Enter
4. 调用 `PUT /api/chat/conversations/{id}/messages/{msg_id}`
5. 该消息之后的所有 assistant 回复被删除
6. 流式输出新的回复

**与 regenerate 的关系**：
- 两者共享"删除后续消息 → 重新生成"的核心逻辑
- 可以抽取公共函数 `delete_messages_after_and_regenerate()`

---

## 功能 6：PDF 导出 + 分享链接

### 需求

- 导出对话为 PDF 格式
- 生成分享链接，允许未登录用户只读访问某段对话

### 技术方案

#### PDF 导出

**依赖库**：`fpdf2` 或 `weasyprint`

**新增 API**：`GET /api/chat/conversations/{id}/export?format=pdf`

**实现逻辑**：

```python
# services/chat_service.py 新增函数
def export_conversation_pdf(
    db: Session,
    user_id: str,
    conversation_id: str,
) -> bytes:
    """导出对话为 PDF 格式"""
    from fpdf import FPDF
    
    conv = get_conversation(db, user_id, conversation_id)
    messages = get_history(db, conversation_id)
    
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=16)
    pdf.cell(200, 10, txt=conv.title, ln=True)
    
    pdf.set_font("Arial", size=10)
    for msg in messages:
        role = "用户" if msg.role == "user" else "助手"
        pdf.cell(200, 10, txt=f"[{role}]", ln=True)
        pdf.multi_cell(200, 10, txt=msg.content)
        pdf.ln(5)
    
    return pdf.output()
```

**注意**：中文支持需要引入中文字体（如 `SimSun.ttf`）

#### 分享链接

**数据模型**：

```python
# models/shared_conversation.py
class SharedConversation(Base):
    __tablename__ = "shared_conversations"
    
    id = Column(String(36), primary_key=True)
    conversation_id = Column(String(36), ForeignKey("conversations.id"))
    token = Column(String(64), unique=True, index=True)  # 短链接 token
    expires_at = Column(DateTime, nullable=True)  # 过期时间
    password = Column(String(128), nullable=True)  # 可选密码保护
    created_at = Column(DateTime, server_default=func.now())
```

**新增 API**：

```python
# POST /api/chat/conversations/{id}/share
{
    "expires_in_days": 7,      # 过期时间（天）
    "password": "abc123"       # 可选密码
}

# 响应
{
    "share_url": "https://your-domain.com/shared/abc123",
    "token": "abc123",
    "expires_at": "2026-05-17T09:00:00"
}

# GET /api/shared/{token}?password=abc123
# 响应：对话内容（无需登录）
```

**前端**：
- 新增 `/shared/:token` 路由
- 只读展示对话内容，无输入框
- 如果有密码保护，先显示密码输入框

---

## 数据库迁移

### Migration 1：Message 新增 tool_calls 字段

```python
# alembic/versions/xxx_add_tool_calls.py
def upgrade():
    op.add_column('messages', sa.Column('tool_calls', sa.JSON, nullable=True))

def downgrade():
    op.drop_column('messages', 'tool_calls')
```

### Migration 2：新增 shared_conversations 表

```python
# alembic/versions/xxx_create_shared_conversations.py
def upgrade():
    op.create_table(
        'shared_conversations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('conversation_id', sa.String(36), sa.ForeignKey('conversations.id')),
        sa.Column('token', sa.String(64), unique=True, index=True),
        sa.Column('expires_at', sa.DateTime, nullable=True),
        sa.Column('password', sa.String(128), nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )

def downgrade():
    op.drop_table('shared_conversations')
```

---

## 开发排期

| 天数 | 功能 | 任务 |
|------|------|------|
| 第 1 天 | 全文搜索 | 后端 API + 服务层实现 |
| 第 2 天 | 全文搜索 | 前端搜索框 + 结果展示 + 跳转定位 |
| 第 3 天 | 导出 Markdown | 后端导出 API |
| 第 4 天 | 导出 Markdown | 前端导出按钮 + 下载 |
| 第 5 天 | 时间线 | Message 模型变更 + Alembic 迁移 |
| 第 6 天 | 时间线 | ChatEngine 改造 + 工具调用序列记录 |
| 第 7 天 | 时间线 | 前端 ToolCallCard 时间线组件 |
| 第 8 天 | regenerate | 后端 regenerate API |
| 第 9 天 | regenerate | 前端重新生成按钮 + 流式替换 |
| 第 10 天 | 编辑消息 | 后端 edit API + 消息链截断逻辑 |
| 第 11 天 | 编辑消息 | 前端 inline edit 组件 |
| 第 12 天 | PDF 导出 | 后端 PDF 生成（fpdf2 + 中文字体） |
| 第 13 天 | 分享链接 | 数据模型 + 分享 API |
| 第 14 天 | 分享链接 | 前端只读分享页面 |
| 第 15 天 | 联调测试 | 全功能回归测试 + Bug 修复 |

---

## 技术风险

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| PostgreSQL LIKE 搜索性能 | 数据量大时搜索慢 | 启用 pg_trgm 索引或 tsvector 全文索引 |
| PDF 中文支持 | 中文显示乱码 | 引入中文字体文件 |
| 消息链截断逻辑 | 编辑消息后上下文不一致 | 严格按时间顺序删除后续消息 |
| 分享链接安全 | Token 被暴力破解 | 使用长随机 Token + 速率限制 |

---

## 验收标准

### 功能 1：全文搜索
- [ ] 搜索关键词能匹配消息内容
- [ ] 搜索结果按对话分组显示
- [ ] 点击结果能跳转并定位到消息
- [ ] 分页正常工作

### 功能 2：导出 Markdown
- [ ] 导出文件格式正确
- [ ] 包含对话标题和导出时间
- [ ] 消息角色标识正确

### 功能 3：时间线
- [ ] 工具调用序列正确记录
- [ ] 时间线 UI 展示正确
- [ ] 已有消息（tool_calls=null）不显示时间线
- [ ] 错误状态用红色高亮

### 功能 4：regenerate
- [ ] 重新生成不重复存储 user message
- [ ] 流式输出正常
- [ ] 工具调用序列正确更新

### 功能 5：编辑消息
- [ ] 编辑后消息内容更新
- [ ] 后续消息正确删除
- [ ] 重新生成正常

### 功能 6：PDF + 分享
- [ ] PDF 导出中文显示正常
- [ ] 分享链接可访问
- [ ] 密码保护正常工作
- [ ] 过期链接无法访问
