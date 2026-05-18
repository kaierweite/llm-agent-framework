"""
Redis 客户端 —— 全局单例连接。

用法：
    from llm_agent.redis_client import get_redis
    get_redis().get("key")
"""

from __future__ import annotations

import os
import threading

import redis as _redis

from llm_agent.config import settings

# 全局单例，惰性初始化
_client: _redis.Redis | None = None
_lock = threading.Lock()


def get_redis() -> _redis.Redis:
    """返回全局 Redis 连接（惰性创建，线程安全）。"""
    global _client
    if _client is None:
        with _lock:
            if _client is None:
                pool = _redis.ConnectionPool.from_url(
                    settings.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                    max_connections=20,
                )
                _client = _redis.Redis(connection_pool=pool)
    return _client


def reinit_redis():
    """在 Gunicorn post_fork 中调用，为每个 worker 重建独立的 Redis 连接。

    fork 之后父进程的 Redis 连接不能被子进程共享。
    """
    global _client
    with _lock:
        _client = None
    get_redis()
    print(f"[worker {os.getpid()}] Redis 连接已重建")


# 便捷别名
redis_client = get_redis  # noqa: E731
