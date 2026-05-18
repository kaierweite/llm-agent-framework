"""
RedisChatHistory —— 基于 Redis 的上下文压缩与持久化记忆系统。

存储结构：
  win:{uid}:{sid}   List   滑动窗口（最近 N 条消息）  TTL 24h
  sum:{uid}:{sid}   String 历史摘要                   无 TTL（主动删除）
  pending:{uid}     List   未完成任务（跨 session）    无 TTL
  prefs:{uid}       Hash   用户偏好                   无 TTL
  facts:{uid}       Hash   重要事实                   无 TTL
  tool:{name}:{h}   String 工具结果缓存               TTL 10min
"""

from __future__ import annotations

import json
import hashlib
import threading
from typing import Callable, Optional, List, Dict, Any

from llm_agent.redis_client import get_redis

# ── 常量 ──────────────────────────────────────────────────────────────
WINDOW_SIZE = 15          # 滑动窗口保留的消息轮数（1 轮 = user + assistant）
THRESHOLD_TOKENS = 30000  # 触发压缩的 token 阈值
SUMMARY_MAX_TOKENS = 1500 # 摘要硬上限（从 500 调到 1500，减少信息丢失）
TOOL_CACHE_TTL = 600      # 工具缓存 10 分钟
WINDOW_TTL = 86400        # 滑动窗口 24 小时

# ── Token 估算 ────────────────────────────────────────────────────────
try:
    import tiktoken
    _enc = tiktoken.encoding_for_model("gpt-4")
    def estimate_tokens(text: str) -> int:
        return len(_enc.encode(text))
except Exception:
    # tiktoken 不可用时的近似估算
    def estimate_tokens(text: str) -> int:
        cn = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        en = len(text) - cn
        return int(cn / 1.5 + en / 4)


def _estimate_messages_tokens(messages: list[dict]) -> int:
    """估算消息列表的 token 数。"""
    total = 0
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            total += estimate_tokens(content)
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and "text" in part:
                    total += estimate_tokens(part["text"])
    return total


class RedisChatHistory:
    """
    基于 Redis 的聊天历史管理器。

    参数：
      user_id:      用户唯一标识
      session_id:   会话 ID（对应 conversation_id）
      llm_caller:   LLM 调用函数（用于生成摘要）
      summary_prompt_getter: 获取摘要 system prompt 的函数
      db_session:   SQLAlchemy Session（用于查询全量历史）
    """

    def __init__(
        self,
        user_id: str,
        session_id: str,
        llm_caller: Callable,
        summary_prompt_getter: Callable[[], str],
        db_session=None,
    ):
        self.user_id = user_id
        self.session_id = session_id
        self.llm_caller = llm_caller
        self.summary_prompt_getter = summary_prompt_getter
        self.db_session = db_session

        self._redis = get_redis()
        self._lock = threading.Lock()

        # 内存缓存（每轮更新后刷新）
        self.conversation_history: list[dict] = []

        # 初始化：从 Redis 加载滑动窗口
        self._load_window()

    # ── Key 生成 ──────────────────────────────────────────────────────

    def _key_window(self) -> str:
        return f"win:{self.user_id}:{self.session_id}"

    def _key_summary(self) -> str:
        return f"sum:{self.user_id}:{self.session_id}"

    def _key_pending(self) -> str:
        return f"pending:{self.user_id}"

    def _key_prefs(self) -> str:
        return f"prefs:{self.user_id}"

    def _key_facts(self) -> str:
        return f"facts:{self.user_id}"

    def _key_tool_cache(self, tool_name: str, args_hash: str) -> str:
        return f"tool:{tool_name}:{args_hash}"

    # ── 滑动窗口操作 ──────────────────────────────────────────────────

    def _load_window(self):
        """从 Redis 加载滑动窗口到内存。"""
        raw = self._redis.lrange(self._key_window(), 0, -1)
        self.conversation_history = [json.loads(m) for m in raw]

    def _save_window(self):
        """将内存中的对话历史写入 Redis 滑动窗口。"""
        key = self._key_window()
        pipe = self._redis.pipeline()
        pipe.delete(key)
        for msg in self.conversation_history:
            pipe.rpush(key, json.dumps(msg, ensure_ascii=False))
        pipe.expire(key, WINDOW_TTL)
        pipe.execute()

    # ── 摘要操作 ──────────────────────────────────────────────────────

    def get_summary(self) -> Optional[str]:
        """获取当前 session 的摘要。"""
        return self._redis.get(self._key_summary())

    def set_summary(self, summary: str):
        """设置摘要（无 TTL）。"""
        self._redis.set(self._key_summary(), summary)

    def delete_summary(self):
        """删除摘要（在 prefs/facts/pending 变化时调用）。"""
        self._redis.delete(self._key_summary())

    # ── 长期记忆操作 ──────────────────────────────────────────────────

    def get_prefs(self) -> Dict[str, str]:
        """获取用户偏好（Hash）。"""
        return self._redis.hgetall(self._key_prefs())

    def set_pref(self, key: str, value: str):
        """设置偏好（覆盖旧值）。"""
        self._redis.hset(self._key_prefs(), key, value)
        self.delete_summary()

    def remove_pref(self, key: str):
        """删除偏好。"""
        self._redis.hdel(self._key_prefs(), key)
        self.delete_summary()

    def get_facts(self) -> Dict[str, str]:
        """获取重要事实（Hash）。"""
        return self._redis.hgetall(self._key_facts())

    def set_fact(self, key: str, value: str):
        """设置事实。"""
        self._redis.hset(self._key_facts(), key, value)
        self.delete_summary()

    def remove_fact(self, key: str):
        """删除事实。"""
        self._redis.hdel(self._key_facts(), key)
        self.delete_summary()

    def get_pending(self) -> List[str]:
        """获取未完成任务。"""
        return self._redis.lrange(self._key_pending(), 0, -1)

    def add_pending(self, task: str):
        """添加任务。"""
        self._redis.rpush(self._key_pending(), task)
        self.delete_summary()

    def remove_pending(self, task: str):
        """删除任务（lrem）。"""
        self._redis.lrem(self._key_pending(), 0, task)
        self.delete_summary()

    # ── 工具结果缓存 ──────────────────────────────────────────────────

    def get_tool_cache(self, tool_name: str, args: str) -> Optional[str]:
        """获取工具结果缓存。"""
        args_hash = hashlib.md5(args.encode()).hexdigest()[:12]
        return self._redis.get(self._key_tool_cache(tool_name, args_hash))

    def set_tool_cache(self, tool_name: str, args: str, result: str):
        """设置工具结果缓存（10 分钟 TTL）。"""
        args_hash = hashlib.md5(args.encode()).hexdigest()[:12]
        # 压缩：如果结果太长，截断并添加标记
        if estimate_tokens(result) > 2000:
            result = result[:2000] + "\n...[已截断]"
        self._redis.setex(
            self._key_tool_cache(tool_name, args_hash),
            TOOL_CACHE_TTL,
            result,
        )

    # ── Token 估算 ────────────────────────────────────────────────────

    def calculate_context_length(self, new_message: str = "") -> int:
        """估算当前上下文的总 token 数。"""
        total = 0
        total += _estimate_messages_tokens(self.conversation_history)
        total += _estimate_messages_tokens(
            [{"content": json.dumps(self.get_prefs(), ensure_ascii=False)}]
        )
        total += _estimate_messages_tokens(
            [{"content": json.dumps(self.get_facts(), ensure_ascii=False)}]
        )
        pending = self.get_pending()
        if pending:
            total += _estimate_messages_tokens(
                [{"content": "\n".join(pending)}]
            )
        summary = self.get_summary()
        if summary:
            total += estimate_tokens(summary)
        if new_message:
            total += estimate_tokens(new_message)
        return total

    def should_summarize(self, new_message: str = "") -> bool:
        """判断是否需要触发压缩。"""
        return self.calculate_context_length(new_message) > THRESHOLD_TOKENS

    # ── 摘要生成 ──────────────────────────────────────────────────────

    def _fetch_old_messages_from_db(self) -> list[dict]:
        """
        从数据库查询窗口外的历史消息（游标分页，不用 OFFSET）。
        返回格式：[{"role": "user", "content": "..."}, ...]
        """
        if not self.db_session:
            return []

        from llm_agent.models.message import Message
        from sqlalchemy import desc

        # 先获取窗口内最早消息的 ID，作为游标
        window_msgs = self.conversation_history
        if not window_msgs:
            # 窗口为空，取最近的 200 条
            rows = (
                self.db_session.query(Message)
                .filter(Message.conversation_id == self.session_id)
                .order_by(desc(Message.created_at))
                .limit(200)
                .all()
            )
            rows.reverse()
        else:
            # 取窗口外的消息
            rows = (
                self.db_session.query(Message)
                .filter(Message.conversation_id == self.session_id)
                .order_by(desc(Message.created_at))
                .limit(500)
                .all()
            )
            rows.reverse()
            # 只保留窗口外的部分
            if len(rows) > len(window_msgs):
                rows = rows[: len(rows) - len(window_msgs)]

        # 粗筛：消息数 > 200 时只保留 user，否则保留 user + assistant
        if len(rows) > 200:
            rows = [r for r in rows if r.role == "user"]
        else:
            rows = [r for r in rows if r.role in ("user", "assistant")]

        return [{"role": r.role, "content": r.content} for r in rows]

    def refresh_summary(self):
        """
        从数据库拉取窗口外历史，调用 LLM 生成 ≤500 token 的摘要。
        摘要只总结对话内容，不包含 prefs/facts/pending。
        """
        old_messages = self._fetch_old_messages_from_db()
        if not old_messages:
            return

        # 构造摘要 prompt
        summary_system = self.summary_prompt_getter()
        dialogue_text = "\n".join(
            f"[{m['role']}] {m['content']}" for m in old_messages
        )

        messages = [
            {"role": "system", "content": summary_system},
            {
                "role": "user",
                "content": (
                    f"请将以下对话压缩为结构化摘要，严格控制不超过 {SUMMARY_MAX_TOKENS} tokens。\n"
                    f"请按以下格式输出：\n"
                    f"## 用户画像\n（用户的身份、角色、偏好）\n"
                    f"## 核心需求\n（用户的主要问题和意图）\n"
                    f"## 已完成事项\n（对话中已解决的问题、已执行的操作）\n"
                    f"## 关键信息\n（对话中提到的重要数据、结论、实体）\n"
                    f"## 待办/未解决\n（用户尚未完成或后续需要跟进的事项）\n\n"
                    f"{dialogue_text}"
                ),
            },
        ]

        summary = self.llm_caller(messages)

        # 后处理：用 tiktoken 截断保底
        try:
            import tiktoken
            enc = tiktoken.encoding_for_model("gpt-4")
            tokens = enc.encode(summary)
            if len(tokens) > SUMMARY_MAX_TOKENS:
                summary = enc.decode(tokens[:SUMMARY_MAX_TOKENS])
        except Exception:
            pass

        self.set_summary(summary)

    # ── 核心接口 ──────────────────────────────────────────────────────

    def add(self, user_input: str, assistant_response: str):
        """
        添加一轮对话到滑动窗口，并触发必要的压缩/更新。
        """
        with self._lock:
            # 添加到内存
            self.conversation_history.append(
                {"role": "user", "content": user_input}
            )
            self.conversation_history.append(
                {"role": "assistant", "content": assistant_response}
            )

            # 滑动窗口裁剪
            max_messages = WINDOW_SIZE * 2  # 每轮 2 条消息
            if len(self.conversation_history) > max_messages:
                self.conversation_history = self.conversation_history[-max_messages:]

            # 保存到 Redis
            self._save_window()

            # 检查是否需要压缩
            if self.should_summarize():
                self.refresh_summary()

    def build_messages(
        self,
        system_prompt: str,
        user_input: str = None,
        knowledge_context: str = None,
    ) -> list[dict]:
        """
        构建发送给 LLM 的完整消息列表。

        上下文拼接顺序：
        1. system prompt
        2. 偏好（prefs）
        3. 事实（facts）
        4. 未完成任务（pending）
        5. 历史摘要（summary）
        6. 滑动窗口（window）
        7. 知识库上下文（可选）
        8. 用户新消息（可选）
        """
        messages = [{"role": "system", "content": system_prompt}]

        # 注入长期记忆
        prefs = self.get_prefs()
        if prefs:
            prefs_text = "、".join(f"{k}={v}" for k, v in prefs.items())
            messages.append({
                "role": "system",
                "content": f"【用户偏好】{prefs_text}",
            })

        facts = self.get_facts()
        if facts:
            facts_text = "、".join(f"{k}={v}" for k, v in facts.items())
            messages.append({
                "role": "system",
                "content": f"【重要事实】{facts_text}",
            })

        pending = self.get_pending()
        if pending:
            pending_text = "\n".join(f"- {t}" for t in pending)
            messages.append({
                "role": "system",
                "content": f"【未完成任务】\n{pending_text}",
            })

        summary = self.get_summary()
        if summary:
            messages.append({
                "role": "system",
                "content": f"【历史摘要】{summary}",
            })

        # 滑动窗口
        messages.extend(self.conversation_history)

        # 知识库上下文
        if knowledge_context:
            messages.append({
                "role": "system",
                "content": f"【知识库参考】\n{knowledge_context}",
            })

        # 用户新消息
        if user_input:
            messages.append({"role": "user", "content": user_input})

        return messages

    def clear(self):
        """清空当前 session 的所有 Redis 数据。"""
        keys = [
            self._key_window(),
            self._key_summary(),
        ]
        self._redis.delete(*keys)
        self.conversation_history = []

    def clear_all_user_data(self):
        """清空该用户的所有数据（prefs/facts/pending + 当前 session）。"""
        keys = [
            self._key_window(),
            self._key_summary(),
            self._key_pending(),
            self._key_prefs(),
            self._key_facts(),
        ]
        self._redis.delete(*keys)
        self.conversation_history = []
