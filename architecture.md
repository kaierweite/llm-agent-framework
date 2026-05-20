# LLM Agent Framework 架构图

## 系统整体架构

```mermaid
graph TB
    subgraph Frontend["🎨 前端层"]
        VUE["Vue 3 + TypeScript<br/>管理后台"]
        SSE_CLIENT["SSE 流式接收"]
    end

    subgraph Gateway["🔐 网关 / 中间件"]
        JWT["JWT 鉴权"]
        RL["请求限流<br/>(令牌桶)"]
        LOG["请求日志"]
        CB["熔断器<br/>(CircuitBreaker)"]
    end

    subgraph API["📡 API 层 (FastAPI Routers)"]
        AUTH_API["认证"]
        CHAT_API["对话"]
        USER_API["用户管理"]
        DEPT_API["部门管理"]
        KB_API["知识库"]
        SKILL_API["技能管理"]
        SHARE_API["知识库分享"]
        ADMIN_API["系统管理"]
    end

    subgraph Core["🧠 核心 Agent 引擎"]
        direction TB
        AGENT["Agent 循环<br/>(ReAct 范式)"]
        PROMPT["Prompt 管理"]
        TOOL_EXEC["工具执行器<br/>(ThreadPoolExecutor)"]
        HISTORY["对话历史管理"]
        MEMORY["长期记忆<br/>(偏好/事实/任务)"]
        SKILL_LOAD["技能加载器"]
        CONTEXT_COMP["上下文压缩<br/>(滑动窗口+自动摘要)"]
    end

    subgraph Services["⚙️ 服务层"]
        AUTH_SVC["认证服务"]
        CHAT_SVC["对话服务"]
        KB_SVC["知识库服务"]
        DEPT_SVC["部门服务"]
        SKILL_SVC["技能服务"]
        AUDIT_SVC["审计服务"]
        ANYTHINGLLM["AnythingLLM<br/>集成服务"]
        DOC_PARSER["文档解析<br/>(Word/Excel/PPT/PDF)"]
        LOCAL_RAG["本地 RAG"]
    end

    subgraph Tools["🛠️ 工具注册表"]
        direction LR
        FILE_TOOLS["文件操作<br/>(列出/读取/创建/删除)"]
        NET_TOOLS["网络请求<br/>(HTTP GET/POST)"]
        WEATHER["天气查询"]
        KB_SEARCH["知识库检索"]
        CHAT_SEARCH["聊天历史搜索"]
        SKILL_TOOLS["技能工具"]
    end

    subgraph Data["💾 数据层"]
        PG[("PostgreSQL<br/>持久化存储")]
        REDIS[("Redis<br/>缓存 / 会话 / 记忆")]
        ANYTHINGLLM_DB[("AnythingLLM<br/>向量检索")]
    end

    subgraph External["🌐 外部"]
        LLM["LLM 服务<br/>(OpenAI 兼容 API)"]
    end

    VUE --> JWT
    SSE_CLIENT --> CHAT_API
    JWT --> RL --> LOG --> CB --> API
    API --> Core
    Core --> Services
    Core --> Tools
    Services --> Data
    Tools --> Data
    Core --> LLM
    AGENT --> PROMPT
    AGENT --> TOOL_EXEC
    AGENT --> HISTORY
    AGENT --> MEMORY
    AGENT --> SKILL_LOAD
    AGENT --> CONTEXT_COMP
```

## Agent ReAct 循环流程

```mermaid
flowchart TD
    START(["用户发送消息"]) --> BUILD["1. 构建消息上下文"]
    BUILD --> INJECT["注入：系统提示词 + 长期记忆<br/>+ 技能规则 + 知识库上下文 + 滑动窗口消息"]
    INJECT --> LLM_CALL["2. LLM 推理 (SSE 流式)"]
    LLM_CALL --> PARSE{"3. 解析响应"}
    PARSE -->|无工具调用| OUTPUT["直接输出回复"]
    PARSE -->|含 &lt;function_calls&gt;| EXTRACT["提取工具调用 JSON"]
    EXTRACT --> EXEC["4. 执行工具<br/>(并行: ThreadPoolExecutor<br/>超时: 30s)"]
    EXEC --> INJECT_RESULT["5. 工具结果注入消息"]
    INJECT_RESULT --> CHECK{"6. 循环控制"}
    CHECK -->|"轮次 &lt; 5 且 耗时 &lt; 120s"| LLM_CALL
    CHECK -->|超限| OUTPUT
    OUTPUT --> COMPRESS{"Token &gt; 30k?"}
    COMPRESS -->|是| SUMMARIZE["触发自动摘要压缩"]
    COMPRESS -->|否| MEM_UPDATE["更新长期记忆"]
    SUMMARIZE --> MEM_UPDATE
    MEM_UPDATE --> END(["返回结果给用户"])
```

## 工具调用详细流程

```mermaid
sequenceDiagram
    participant U as 用户
    participant A as Agent 引擎
    participant TR as 工具注册表
    participant T1 as 文件工具
    participant T2 as 网络工具
    participant T3 as 知识库工具
    participant L as LLM

    U->>A: "帮我查天气并整理成文件"
    A->>L: 发送消息 (含工具列表 Schema)
    L-->>A: &lt;function_calls&gt;<br/>[get_weather, create_file]
    A->>TR: 获取工具函数快照
    par 并行执行
        A->>T1: create_file()
        A->>T2: get_weather()
    end
    T2-->>A: 天气数据
    T1-->>A: 文件创建成功
    A->>L: 注入工具结果，继续推理
    L-->>A: 最终回复文本
    A->>U: SSE 流式输出
```

## 上下文压缩与记忆系统

```mermaid
flowchart LR
    subgraph 短期记忆["滑动窗口 (Redis)"]
        MSG1["轮次 1-15<br/>完整保留"]
        MSG2["轮次 16+<br/>移出窗口"]
    end

    subgraph 压缩层["自动摘要"]
        COMP["Token &gt; 30k<br/>触发 LLM 摘要"]
        SUMMARY["结构化摘要<br/>(用户意图/关键信息/执行结果)"]
    end

    subgraph 长期记忆["长期记忆 (Redis)"]
        PREFS["用户偏好<br/>(回复风格=简洁)"]
        FACTS["重要事实<br/>(用户名=张三)"]
        PENDING["未完成任务<br/>(明天提醒开会)"]
    end

    subgraph 上下文构建["消息构建"]
        FINAL["最终 Prompt ="]
        SYS["系统提示词"]
        SKILL["技能规则"]
        SUM["历史摘要"]
        WIN["滑动窗口消息"]
        KB["知识库上下文"]
    end

    MSG2 --> COMP
    COMP --> SUMMARY
    SUMMARY --> SUM
    MSG1 --> WIN
    PREFS --> SYS
    FACTS --> SYS
    PENDING --> SYS
    SYS --> FINAL
    SKILL --> FINAL
    SUM --> FINAL
    WIN --> FINAL
    KB --> FINAL
```

## 数据模型概览

```mermaid
erDiagram
    USER ||--o{ MESSAGE : "发送"
    USER }o--|| DEPARTMENT : "属于"
    USER ||--o{ AUDIT_LOG : "产生"
    USER ||--o{ CONVERSATION : "创建"
    CONVERSATION ||--o{ MESSAGE : "包含"
    KNOWLEDGE_BASE ||--o{ DOCUMENT : "包含"
    KNOWLEDGE_BASE ||--o{ KB_MEMBER : "有成员"
    USER ||--o{ KB_MEMBER : "是"
    KNOWLEDGE_BASE ||--o{ KB_SHARE : "生成分享码"
    KNOWLEDGE_BASE ||--o{ KB_ACCESS_LOG : "被访问"
    SKILL ||--o{ USER : "被启用"

    USER {
        int id PK
        string username
        string password_hash
        string role
        int department_id FK
        bool is_active
    }
    DEPARTMENT {
        int id PK
        string name
        int parent_id FK
        string path
    }
    CONVERSATION {
        int id PK
        int user_id FK
        string title
        datetime created_at
    }
    MESSAGE {
        int id PK
        int conversation_id FK
        int user_id FK
        string role
        text content
        json tool_calls
    }
    KNOWLEDGE_BASE {
        int id PK
        string name
        string description
        int owner_id FK
    }
    DOCUMENT {
        int id PK
        int kb_id FK
        string filename
        string file_path
        string file_type
    }
    SKILL {
        int id PK
        string name
        string path
        bool is_active
    }
    AUDIT_LOG {
        int id PK
        int user_id FK
        string action
        string ip_address
        int duration_ms
        string trace_id
    }
```

## 部署架构

```mermaid
graph TB
    subgraph 用户端["👤 用户"]
        BROWSER["浏览器"]
    end

    subgraph 服务器["🖥️ 服务器"]
        NGINX["Nginx<br/>(反向代理 + 静态资源)"]
        GUNICORN["Gunicorn<br/>(4 workers)"]
        FASTAPI_APP["FastAPI 应用"]
    end

    subgraph 数据服务["🗄️ 数据服务"]
        PG_DB[("PostgreSQL<br/>:5432")]
        REDIS_DB[("Redis<br/>:6379")]
        ANYTHINGLLM_SVC[("AnythingLLM<br/>:3001")]
    end

    subgraph 外部服务["☁️ 外部"]
        LLM_API["LLM API<br/>(OpenAI 兼容)"]
    end

    BROWSER -->|"HTTPS :443"| NGINX
    NGINX -->|"/api"| GUNICORN
    NGINX -->|"/ "| NGINX
    GUNICORN --> FASTAPI_APP
    FASTAPI_APP --> PG_DB
    FASTAPI_APP --> REDIS_DB
    FASTAPI_APP --> ANYTHINGLLM_SVC
    FASTAPI_APP -->|"httpx 连接池"| LLM_API
```
