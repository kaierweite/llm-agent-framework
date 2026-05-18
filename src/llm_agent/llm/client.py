import json
import re
import ssl
import asyncio
import logging
import threading
import time
from typing import Optional, Callable, AsyncIterator

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_not_exception_type,
    before_sleep_log,
)

logger = logging.getLogger(__name__)


class ContextLengthExceededError(Exception):
    """LLM 返回 context_length_exceeded 错误，需要截断消息后重试。"""
    pass


class CircuitBreakerOpenError(Exception):
    """熔断器开启，LLM 服务暂时不可用。"""
    pass


class CircuitBreaker:
    """简单熔断器：连续失败 N 次后熔断，冷却 M 秒后半开尝试。"""

    def __init__(self, failure_threshold: int = 5, cooldown_seconds: int = 60):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self._failure_count = 0
        self._last_failure_time: float = 0
        self._state = "closed"  # closed / open / half-open

    @property
    def state(self) -> str:
        if self._state == "open":
            if time.time() - self._last_failure_time >= self.cooldown_seconds:
                self._state = "half-open"
        return self._state

    def record_success(self):
        self._failure_count = 0
        self._state = "closed"

    def record_failure(self):
        self._failure_count += 1
        self._last_failure_time = time.time()
        if self._failure_count >= self.failure_threshold:
            self._state = "open"

    def allow_request(self) -> bool:
        state = self.state
        return state in ("closed", "half-open")


class LLMClient:
    def __init__(self, base_url: str, api_key: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self._async_client: Optional[httpx.AsyncClient] = None
        self._sync_client: Optional[httpx.Client] = None
        self._sync_lock = threading.Lock()
        self.breaker = CircuitBreaker(failure_threshold=5, cooldown_seconds=60)

    # ------------------------------------------------------------------
    # httpx 客户端（复用连接池，避免每次请求都建连）
    # ------------------------------------------------------------------
    def _get_async_client(self) -> httpx.AsyncClient:
        if self._async_client is None or self._async_client.is_closed:
            self._async_client = httpx.AsyncClient(
                timeout=httpx.Timeout(connect=10, read=120, write=10, pool=10),
                limits=httpx.Limits(
                    max_connections=50,
                    max_keepalive_connections=20,
                    keepalive_expiry=30,
                ),
                verify=False,
            )
        return self._async_client

    def _get_sync_client(self) -> httpx.Client:
        """复用同步 httpx.Client，线程安全。"""
        with self._sync_lock:
            if self._sync_client is None or self._sync_client.is_closed:
                self._sync_client = httpx.Client(
                    timeout=httpx.Timeout(connect=10, read=120, write=10, pool=10),
                    limits=httpx.Limits(
                        max_connections=20,
                        max_keepalive_connections=10,
                        keepalive_expiry=30,
                    ),
                    verify=False,
                )
            return self._sync_client

    def _is_openrouter(self) -> bool:
        return self.base_url and "openrouter" in self.base_url.lower()

    def _get_headers(self) -> dict:
        headers = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "Authorization": f"Bearer {self.api_key}",
        }
        if self._is_openrouter():
            headers["HTTP-Referer"] = "https://github.com"
            headers["X-Title"] = "AI-Chat-Client"
        return headers

    # ------------------------------------------------------------------
    # SSE 流式解析（同步 + 异步共用逻辑）
    # ------------------------------------------------------------------
    @staticmethod
    def _parse_sse_line(line: str, on_chunk: Optional[Callable[[str], None]] = None) -> tuple:
        """解析一行 SSE 数据，返回 (content, done)"""
        if not line.startswith("data:"):
            return None, False
        data = line[5:].strip()
        if data == "[DONE]":
            return None, True
        try:
            json_data = json.loads(data)
            choices = json_data.get("choices", [{}])
            if not choices:
                return None, False
            delta = choices[0].get("delta", {})
            content = delta.get("content", "")
            if content and on_chunk:
                on_chunk(content)
            return content, False
        except json.JSONDecodeError:
            return None, False

        # ------------------------------------------------------------------
    # 异步流式调用（主推路径，高并发走这里）
    # ------------------------------------------------------------------
    async def async_call_llm(
        self,
        messages: list,
        on_chunk: Optional[Callable[[str], None]] = None,
    ) -> str:
        if not self.breaker.allow_request():
            raise CircuitBreakerOpenError(
                f"LLM 熔断器开启中，冷却 {self.breaker.cooldown_seconds}s，"
                f"已连续失败 {self.breaker._failure_count} 次"
            )

        last_error = None
        retryer = retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_not_exception_type((ContextLengthExceededError, CircuitBreakerOpenError)),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )

        async def _do_request():
            nonlocal last_error
            client = self._get_async_client()
            url = f"{self.base_url}/chat/completions"
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": True,
                "max_tokens": 51200,
            }
            full_content: list[str] = []
            async with client.stream(
                "POST", url, json=payload, headers=self._get_headers()
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line:
                        continue
                    content, done = self._parse_sse_line(line, on_chunk)
                    if content:
                        full_content.append(content)
                    if done:
                        break
            return "".join(full_content).strip()

        try:
            result = await retryer(_do_request)()
            self.breaker.record_success()
            return result
        except ContextLengthExceededError:
            raise
        except CircuitBreakerOpenError:
            raise
        except Exception as e:
            error_str = str(e).lower()
            if "context_length_exceeded" in error_str or "maximum context length" in error_str:
                raise ContextLengthExceededError(str(e)) from e
            self.breaker.record_failure()
            raise

        # ------------------------------------------------------------------
    # 同步调用（复用 httpx.Client，不再每次 new）
    # ------------------------------------------------------------------
    def call_llm(
        self,
        messages: list,
        stream: bool = True,
        on_chunk: Optional[Callable[[str], None]] = None,
    ) -> str:
        if not self.breaker.allow_request():
            raise CircuitBreakerOpenError(
                f"LLM 熔断器开启中，冷却 {self.breaker.cooldown_seconds}s，"
                f"已连续失败 {self.breaker._failure_count} 次"
            )

        retryer = retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_not_exception_type((ContextLengthExceededError, CircuitBreakerOpenError)),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )

        def _do_request():
            client = self._get_sync_client()
            url = f"{self.base_url}/chat/completions"
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": stream,
                "max_tokens": 51200,
            }
            full_content: list[str] = []
            with client.stream(
                "POST", url, json=payload, headers=self._get_headers()
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    line = line.strip()
                    if not line:
                        continue
                    content, done = self._parse_sse_line(line, on_chunk)
                    if content:
                        full_content.append(content)
                    if done:
                        break
            return "".join(full_content).strip()

        try:
            result = retryer(_do_request)()
            self.breaker.record_success()
            return result
        except ContextLengthExceededError:
            raise
        except CircuitBreakerOpenError:
            raise
        except Exception as e:
            error_str = str(e).lower()
            if "context_length_exceeded" in error_str or "maximum context length" in error_str:
                raise ContextLengthExceededError(str(e)) from e
            self.breaker.record_failure()
            raise

    # ------------------------------------------------------------------
    # 工具调用标签清理（不变）
    # ------------------------------------------------------------------
    def _find_matching_bracket(self, text: str, start: int) -> int:
        depth = 0
        in_string = False
        escape = False
        for i in range(start, len(text)):
            ch = text[i]
            if escape:
                escape = False
                continue
            if ch == "\\" and in_string:
                escape = True
                continue
            if ch == '"' and not escape:
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    return i
        return -1

    def _strip_tool_call_tags(self, text: str) -> str:
        text = re.sub(r"```json\s*<function_calls>.*?</function_calls>\s*```", "", text, flags=re.DOTALL)
        text = re.sub(r"<function_calls>.*?</function_calls>", "", text, flags=re.DOTALL)
        text = re.sub(r"<tool_calls>.*?</tool_calls>", "", text, flags=re.DOTALL)
        result = []
        i = 0
        while i < len(text):
            if text[i] == "[":
                end = self._find_matching_bracket(text, i)
                if end != -1:
                    candidate = text[i : end + 1]
                    try:
                        parsed = json.loads(candidate)
                        if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict) and "name" in parsed[0]:
                            i = end + 1
                            continue
                    except (json.JSONDecodeError, ValueError):
                        pass
            result.append(text[i])
            i += 1
        return "".join(result).strip()

    def strip_tool_call_tags(self, text: str) -> str:
        return self._strip_tool_call_tags(text)

    async def close(self):
        if self._async_client and not self._async_client.is_closed:
            await self._async_client.aclose()
        with self._sync_lock:
            if self._sync_client and not self._sync_client.is_closed:
                self._sync_client.close()
