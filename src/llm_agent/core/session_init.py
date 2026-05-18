"""
Session 初始化模块 —— 异步加载窗口 + 复制上次摘要。

新 session 启动时：
1. 同步复制最近一次 session 的摘要到新 session（冷启动优化）
2. 异步从数据库加载最近 WINDOW_SIZE 条消息到滑动窗口
"""

from __future__ import annotations

import json
import threading
from typing import Optional, Callable

from llm_agent.redis_client import get_redis
from llm_agent.core.redis_history import WINDOW_SIZE


def init_session_summary(
    user_id: str,
    new_session_id: str,
    db_session=None,
) -> Optional[str]:
    """
    同步复制最近一次 session 的摘要到新 session。

    返回复制的摘要内容（若无则返回 None）。
    """
    if not db_session:
        return None

    from llm_agent.models.conversation import Conversation
    from llm_agent.models.message import Message
    from sqlalchemy import desc

    # 查找该用户最近一次有活动的 session
    last_conv = (
        db_session.query(Conversation)
        .filter(Conversation.user_id == user_id)
        .order_by(desc(Conversation.updated_at))
        .first()
    )
    if not last_conv or last_conv.id == new_session_id:
        return None

    # 查找该 session 的摘要（存在 Redis 中）
    redis = get_redis()
    old_summary_key = f"sum:{user_id}:{last_conv.id}"
    summary = redis.get(old_summary_key)

    if summary:
        new_key = f"sum:{user_id}:{new_session_id}"
        redis.set(new_key, summary)
        return summary

    return None


def async_load_window(
    user_id: str,
    session_id: str,
    db_session=None,
    callback: Optional[Callable] = None,
):
    """
    异步从数据库加载最近 WINDOW_SIZE 条消息到滑动窗口。

    参数：
      callback: 加载完成后的回调函数（可选），签名 callback(success: bool)
    """
    def _load():
        try:
            if not db_session:
                if callback:
                    callback(False)
                return

            from llm_agent.models.message import Message
            from sqlalchemy import desc

            # 从数据库拉取最近的消息
            rows = (
                db_session.query(Message)
                .filter(Message.conversation_id == session_id)
                .order_by(desc(Message.created_at))
                .limit(WINDOW_SIZE * 2)  # 每轮 2 条消息
                .all()
            )
            rows.reverse()

            if not rows:
                if callback:
                    callback(False)
                return

            # 写入 Redis 滑动窗口
            redis = get_redis()
            key = f"win:{user_id}:{session_id}"
            pipe = redis.pipeline()
            pipe.delete(key)
            for msg in rows:
                pipe.rpush(
                    key,
                    json.dumps(
                        {"role": msg.role, "content": msg.content},
                        ensure_ascii=False,
                    ),
                )
            pipe.expire(key, 86400)  # 24 小时
            pipe.execute()

            if callback:
                callback(True)

        except Exception as e:
            print(f"[session_init] 异步加载窗口失败: {e}")
            if callback:
                callback(False)

    thread = threading.Thread(target=_load, daemon=True)
    thread.start()
    return thread
