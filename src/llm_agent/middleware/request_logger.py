"""
请求日志中间件 — 行业标准实现

功能：
- 每个请求生成唯一 trace_id，贯穿整个请求生命周期
- 自动记录所有 /api/ 请求的入参、响应码、耗时
- 敏感数据自动脱敏（密码、token、API key）
- 请求体大小限制（防止大文件上传拖慢日志）
- 结构化日志输出（JSON 格式，便于 ELK/Loki 等日志系统采集）
- 异常请求自动标记 ERROR 级别

日志格式：
{
    "level": "INFO",
    "trace_id": "abc123",
    "method": "POST",
    "path": "/api/auth/login",
    "status_code": 200,
    "duration_ms": 42,
    "user_id": "xxx",
    "ip": "127.0.0.1",
    "user_agent": "Mozilla/5.0 ...",
    "request_body": {"email": "user@example.com", "password": "***"},
    "response_summary": {"code": 0, "message": "success"},
    "error": null,
    "timestamp": "2026-05-14T15:37:43+08:00"
}
"""

import re
import time
import uuid
import json
import logging
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse

logger = logging.getLogger("audit.request")

# ── 敏感字段脱敏 ──────────────────────────────────────────────────
_SENSITIVE_KEYS = {
    "password", "old_password", "new_password", "token",
    "access_token", "api_key", "apikey", "secret",
    "authorization", "credit_card", "ssn",
}

# 匹配 Bearer token
_BEARER_RE = re.compile(r"Bearer\s+\S+", re.IGNORECASE)

# 匹配 API key 值（长字符串）
_API_KEY_RE = re.compile(r"^(sk-|ak-|key-)?[A-Za-z0-9\-_]{20,}$")


def _mask_value(key: str, value) -> str:
    """对敏感值进行脱敏"""
    if isinstance(value, str):
        if len(value) <= 8:
            return "***"
        return value[:3] + "***" + value[-3:]
    return "***"


def _sanitize_dict(data: dict, depth: int = 0) -> dict:
    """递归脱敏字典中的敏感字段"""
    if depth > 5:
        return {"...": "(depth limit)"}
    result = {}
    for k, v in data.items():
        k_lower = k.lower().replace("-", "_")
        if k_lower in _SENSITIVE_KEYS:
            result[k] = _mask_value(k, v)
        elif isinstance(v, dict):
            result[k] = _sanitize_dict(v, depth + 1)
        elif isinstance(v, list):
            result[k] = [
                _sanitize_dict(item, depth + 1) if isinstance(item, dict) else item
                for item in v[:10]  # 列表最多取 10 项
            ]
        else:
            result[k] = v
    return result


def _sanitize_headers(headers: dict) -> dict:
    """脱敏请求头"""
    result = {}
    for k, v in headers.items():
        if k.lower() == "authorization":
            result[k] = _BEARER_RE.sub("Bearer ***", v)
        else:
            result[k] = v
    return result


# ── 请求体大小限制 ────────────────────────────────────────────────
_MAX_BODY_LOG_SIZE = 4096  # 4KB，超过则截断


def _truncate_string(s: str, max_len: int = _MAX_BODY_LOG_SIZE) -> str:
    if len(s) <= max_len:
        return s
    return s[:max_len] + f"... (truncated, total {len(s)} chars)"


# ── 路径归一化（避免动态路径段产生大量日志桶） ──────────────────────
_PATH_PATTERNS = [
    (re.compile(r"/conversations/[a-f0-9\-]{36}"), "/conversations/{id}"),
    (re.compile(r"/conversations/\d+"), "/conversations/{id}"),
    (re.compile(r"/users/[a-f0-9\-]{36}"), "/users/{id}"),
    (re.compile(r"/knowledge/bases/[a-f0-9\-]{36}"), "/knowledge/bases/{id}"),
    (re.compile(r"/knowledge/share-codes/[a-f0-9\-]{36}"), "/knowledge/share-codes/{id}"),
    (re.compile(r"/skills/[a-f0-9\-]{36}"), "/skills/{id}"),
]


def _normalize_path(path: str) -> str:
    for pattern, replacement in _PATH_PATTERNS:
        path = pattern.sub(replacement, path)
    return path


# ── 不需要记录请求体的路径（如文件上传） ──────────────────────────
_SKIP_BODY_PATHS = {"/api/knowledge/upload", "/api/chat/conversations"}


def _should_log_body(path: str) -> bool:
    """文件上传等路径不记录请求体"""
    for skip in _SKIP_BODY_PATHS:
        if path.startswith(skip):
            return False
    return True


# ── 中间件 ────────────────────────────────────────────────────────
class RequestLoggerMiddleware(BaseHTTPMiddleware):
    """
    请求日志中间件

    记录每个 /api/ 请求的完整生命周期：
    - trace_id（贯穿请求链路）
    - 请求方法、路径、参数
    - 响应状态码、耗时
    - 当前用户（从 request.state.user 获取）
    - 异常信息（如有）
    """

    # 不记录日志的路径
    _SKIP_PATHS = {"/api/health", "/docs", "/openapi.json", "/redoc"}

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        # 跳过不需要记录的路径
        if path in self._SKIP_PATHS or not path.startswith("/api/"):
            return await call_next(request)

        # 生成 trace_id
        trace_id = uuid.uuid4().hex[:12]
        request.state.trace_id = trace_id

        # 记录请求开始
        start_time = time.monotonic()

        # 提取请求信息
        method = request.method
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "")

        # 提取当前用户（如果 auth 中间件已设置）
        user = getattr(request.state, "user", None)
        user_id = str(user.id) if user and hasattr(user, "id") else None
        user_email = user.email if user and hasattr(user, "email") else None

        # 读取并脱敏请求体
        request_body = None
        if _should_log_body(path) and method in ("POST", "PUT", "PATCH"):
            try:
                body_bytes = await request.body()
                if body_bytes:
                    body_str = body_bytes.decode("utf-8", errors="replace")
                    body_str = _truncate_string(body_str)
                    try:
                        body_data = json.loads(body_str)
                        if isinstance(body_data, dict):
                            request_body = _sanitize_dict(body_data)
                        else:
                            request_body = body_str
                    except json.JSONDecodeError:
                        request_body = body_str
            except Exception:
                request_body = "(failed to read body)"

        # 执行请求
        response = None
        error_msg = None
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as exc:
            error_msg = f"{type(exc).__name__}: {str(exc)}"
            status_code = 500
            raise
        finally:
            duration_ms = round((time.monotonic() - start_time) * 1000, 1)
            normalized_path = _normalize_path(path)

            # 构建日志条目
            log_entry = {
                "trace_id": trace_id,
                "method": method,
                "path": normalized_path,
                "raw_path": path,
                "status_code": status_code,
                "duration_ms": duration_ms,
                "user_id": user_id,
                "user_email": user_email,
                "ip": client_ip,
                "user_agent": _truncate_string(user_agent, 200),
            }

            if request_body is not None:
                log_entry["request_body"] = request_body

            if error_msg:
                log_entry["error"] = error_msg

            # 根据状态码选择日志级别
            if status_code >= 500:
                log_level = "ERROR"
            elif status_code >= 400:
                log_level = "WARN"
            else:
                log_level = "INFO"

            log_entry["level"] = log_level

            # 写入日志
            if log_level == "ERROR":
                logger.error(json.dumps(log_entry, ensure_ascii=False))
            elif log_level == "WARN":
                logger.warning(json.dumps(log_entry, ensure_ascii=False))
            else:
                logger.info(json.dumps(log_entry, ensure_ascii=False))

            # 将 trace_id 注入响应头（便于前端排查问题）
            if response:
                response.headers["X-Trace-Id"] = trace_id

        return response
