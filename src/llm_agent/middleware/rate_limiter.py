"""
基于令牌桶的限流中间件（高并发版）

策略：
- /api/chat/conversations/*/messages/stream  → 每用户 5 req/s（流式聊天是核心资源）
- /api/chat/conversations/*/messages          → 每用户 2 req/s（非流式）
- 其他 /api/ 路由                             → 每用户 20 req/s

实现：
- 优先使用 Redis（多 worker 共享状态，Lua 脚本原子操作）
- Redis 不可用时自动降级为进程内内存限流
- 所有 Redis 操作均为异步，不阻塞 event loop
- URL 路径归一化，避免动态路径段导致限流桶爆炸
"""

import re
import time
import asyncio
import logging
import threading
from collections import defaultdict
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

# ── URL 归一化：将动态路径段替换为占位符 ──────────────────────────
# 防止 /conversations/abc123/messages 和 /conversations/def456/messages
# 被当作两个不同的限流桶
_PATH_NORMALIZERS = [
    (re.compile(r"/conversations/[a-f0-9-]{36}"), "/conversations/{id}"),
    (re.compile(r"/conversations/\d+"), "/conversations/{id}"),
]


def _normalize_path(path: str) -> str:
    for pattern, replacement in _PATH_NORMALIZERS:
        path = pattern.sub(replacement, path)
    return path


# ── 限流规则：(pattern_substring, rate_per_sec, burst_capacity) ────
_RATE_RULES = [
    ("/messages/stream", 5, 10),   # 流式聊天：5/s，突发允许 10
    ("/messages", 2, 4),           # 非流式发消息：2/s
    ("/api/", 20, 40),             # 全局兜底：20/s
]


def _get_rate_limit(path: str) -> tuple[float, int]:
    for pattern, rate, capacity in _RATE_RULES:
        if pattern in path:
            return rate, capacity
    return 20, 40  # 默认


# ── 用户标识提取 ──────────────────────────────────────────────────
def _get_user_id(request: Request) -> str:
    """从 request.state 或 Authorization 提取用户标识"""
    user = getattr(request.state, "user", None)
    if user and hasattr(user, "id"):
        return str(user.id)
    # fallback: 用 IP
    return request.client.host if request.client else "unknown"


# ── 进程内令牌桶 ─────────────────────────────────────────────────
class _TokenBucket:
    """线程安全的进程内令牌桶（单 worker 粒度）"""

    def __init__(self, rate: float, capacity: int):
        self.rate = rate          # 每秒生成的令牌数
        self.capacity = capacity  # 桶容量
        self._buckets: dict[str, float] = {}
        self._last_refill: dict[str, float] = {}
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            tokens = self._buckets.get(key, float(self.capacity))
            last = self._last_refill.get(key, now)

            elapsed = now - last
            tokens = min(self.capacity, tokens + elapsed * self.rate)
            self._last_refill[key] = now

            if tokens >= 1:
                self._buckets[key] = tokens - 1
                return True
            else:
                self._buckets[key] = tokens
                return False

    def cleanup(self, max_age: float = 60.0):
        """清理长时间未使用的桶条目，防止内存泄漏"""
        now = time.monotonic()
        with self._lock:
            stale_keys = [k for k, t in self._last_refill.items() if now - t > max_age]
            for k in stale_keys:
                self._buckets.pop(k, None)
                self._last_refill.pop(k, None)


# ── Redis 令牌桶 Lua 脚本 ────────────────────────────────────────
# 原子操作，保证并发安全
_REDIS_LUA_SCRIPT = """
local key = KEYS[1]
local rate = tonumber(ARGV[1])
local capacity = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local ttl = 30

local bucket = redis.call('HMGET', key, 'tokens', 'last_refill')
local tokens = tonumber(bucket[1])
local last_refill = tonumber(bucket[2])

if tokens == nil then
    tokens = capacity
    last_refill = now
end

local elapsed = now - last_refill
tokens = math.min(capacity, tokens + elapsed * rate)
last_refill = now

if tokens >= 1 then
    tokens = tokens - 1
    redis.call('HMSET', key, 'tokens', tostring(tokens), 'last_refill', tostring(last_refill))
    redis.call('EXPIRE', key, ttl)
    return 1
else
    redis.call('HMSET', key, 'tokens', tostring(tokens), 'last_refill', tostring(last_refill))
    redis.call('EXPIRE', key, ttl)
    return 0
end
"""


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    限流中间件 — 自动在进程内令牌桶和 Redis 之间切换

    多 worker 部署时：
    - Redis 模式：所有 worker 共享限流状态，精确限流
    - 本地模式：每个 worker 独立限流（rate * workers ≈ 总 QPS）
    """

    def __init__(self, app, redis_url: Optional[str] = None):
        super().__init__(app)
        self._redis = None
        self._redis_async = None
        self._local_buckets: dict[str, _TokenBucket] = {}
        self._cleanup_counter = 0

        # 尝试连接 Redis（同步 + 异步）
        if redis_url:
            try:
                import redis as _redis_sync
                self._redis = _redis_sync.from_url(
                    redis_url, decode_responses=True, socket_timeout=1
                )
                self._redis.ping()
                logger.info("限流器使用 Redis 模式")
            except Exception as e:
                logger.warning(f"Redis 同步连接失败: {e}")
                self._redis = None

            try:
                import redis.asyncio as _redis_async
                self._redis_async = _redis_async.from_url(
                    redis_url, decode_responses=True, socket_timeout=1
                )
                logger.info("限流器异步 Redis 连接就绪")
            except Exception as e:
                logger.warning(f"Redis 异步连接失败: {e}")
                self._redis_async = None

        if not self._redis and not self._redis_async:
            logger.info("限流器使用进程内内存模式")

    def _get_local_bucket(self, rate: float, capacity: int) -> _TokenBucket:
        key = f"{rate}:{capacity}"
        if key not in self._local_buckets:
            self._local_buckets[key] = _TokenBucket(rate, capacity)
        return self._local_buckets[key]

    def _check_redis_sync(self, key: str, rate: float, capacity: int) -> bool:
        """同步 Redis 令牌桶（降级用）"""
        try:
            result = self._redis.eval(
                _REDIS_LUA_SCRIPT, 1, key, rate, capacity, time.time()
            )
            return result == 1
        except Exception:
            return True  # fail-open

    async def _check_redis_async(self, key: str, rate: float, capacity: int) -> bool:
        """异步 Redis 令牌桶（主路径）"""
        try:
            result = await self._redis_async.eval(
                _REDIS_LUA_SCRIPT, 1, key, rate, capacity, time.time()
            )
            return result == 1
        except Exception:
            return True  # fail-open

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # 只限流 API 路由
        if not path.startswith("/api/"):
            return await call_next(request)

        # 健康检查不限流
        if path == "/api/health":
            return await call_next(request)

        rate, capacity = _get_rate_limit(path)
        user_id = _get_user_id(request)
        normalized = _normalize_path(path)
        key = f"rl:{user_id}:{normalized}"

        # 选择限流后端：异步 Redis > 同步 Redis > 本地内存
        if self._redis_async:
            allowed = await self._check_redis_async(key, rate, capacity)
        elif self._redis:
            allowed = self._check_redis_sync(key, rate, capacity)
        else:
            bucket = self._get_local_bucket(rate, capacity)
            allowed = bucket.allow(key)

            # 每 1000 次请求清理一次过期条目
            self._cleanup_counter += 1
            if self._cleanup_counter >= 1000:
                self._cleanup_counter = 0
                bucket.cleanup(max_age=60.0)

        if not allowed:
            retry_after = max(1, int(1 / rate) + 1)
            return JSONResponse(
                status_code=429,
                content={"code": 42901, "message": "请求过于频繁，请稍后再试"},
                headers={"Retry-After": str(retry_after)},
            )

        return await call_next(request)
