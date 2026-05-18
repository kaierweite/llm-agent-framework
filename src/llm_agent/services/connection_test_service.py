"""
连接测试与健康检查服务 —— LLM / AnythingLLM / 数据库的连通性测试。
"""

import time
import http.client
import ssl
from urllib.parse import urlparse

from sqlalchemy import text
from sqlalchemy.orm import Session

from llm_agent.config import settings


def test_llm_connection(base_url: str, api_key: str, model: str) -> dict:
    if not base_url:
        return {"status": "error", "message": "LLM_BASE_URL 未配置"}
    parsed = urlparse(base_url)
    scheme = parsed.scheme or "https"
    port = parsed.port or (443 if scheme == "https" else 80)
    conn = None
    try:
        if scheme == "https":
            ctx = ssl.create_default_context()
            conn = http.client.HTTPSConnection(parsed.hostname, port, timeout=30, context=ctx)
        else:
            conn = http.client.HTTPConnection(parsed.hostname, port, timeout=30)
        conn.request("POST", parsed.path or "/v1/chat/completions", headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }, body='{"model":"' + model + '","messages":[{"role":"user","content":"ping"}],"max_tokens":5}')
        resp = conn.getresponse()
        data = resp.read().decode("utf-8", errors="replace")
        if resp.status == 200:
            return {"status": "ok", "message": "连接成功"}
        return {"status": "error", "message": f"HTTP {resp.status}: {data[:200]}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        if conn:
            conn.close()


def test_anythingllm_connection(base_url: str, api_key: str) -> dict:
    if not base_url:
        return {"status": "error", "message": "ANYTHINGLLM_BASE_URL 未配置"}
    parsed = urlparse(base_url)
    scheme = parsed.scheme or "https"
    port = parsed.port or (443 if scheme == "https" else 80)
    conn = None
    try:
        if scheme == "https":
            ctx = ssl.create_default_context()
            conn = http.client.HTTPSConnection(parsed.hostname, port, timeout=30, context=ctx)
        else:
            conn = http.client.HTTPConnection(parsed.hostname, port, timeout=30)
        conn.request("GET", parsed.path or "/api/v1/system", headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
        })
        resp = conn.getresponse()
        data = resp.read().decode("utf-8", errors="replace")
        if resp.status == 200:
            return {"status": "ok", "message": "连接成功"}
        return {"status": "error", "message": f"HTTP {resp.status}: {data[:200]}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        if conn:
            conn.close()


def test_miot_connection(base_url: str, api_key: str) -> dict:
    if not base_url:
        return {"status": "error", "message": "MIOT_BASE_URL 未配置"}
    parsed = urlparse(base_url)
    conn = None
    try:
        scheme = parsed.scheme or "https"
        port = parsed.port or (443 if scheme == "https" else 80)
        conn_cls = http.client.HTTPSConnection if scheme == "https" else http.client.HTTPConnection
        ctx = ssl.create_default_context() if scheme == "https" else None
        conn = conn_cls(parsed.hostname, port, timeout=30, context=ctx)
        conn.request("GET", parsed.path or "/", headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
        })
        resp = conn.getresponse()
        data = resp.read().decode("utf-8", errors="replace")
        if resp.status == 200:
            return {"status": "ok", "message": "连接成功"}
        return {"status": "error", "message": f"HTTP {resp.status}: {data[:200]}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        if conn:
            conn.close()


def get_health_check(db: Session) -> dict:
    db_status = "ok"
    db_latency = 0
    try:
        t0 = time.time()
        db.execute(text("SELECT 1"))
        db_latency = int((time.time() - t0) * 1000)
    except Exception:
        db_status = "error"
        db_latency = -1

    t0 = time.time()
    llm_result = test_llm_connection(settings.llm_base_url, settings.llm_api_key, settings.llm_model)
    llm_latency = int((time.time() - t0) * 1000)

    t0 = time.time()
    anythingllm_result = test_anythingllm_connection(settings.anythingllm_base_url, settings.anythingllm_api_key)
    anythingllm_latency = int((time.time() - t0) * 1000)

    return {
        "database": {"status": db_status, "latency_ms": db_latency},
        "llm": {"status": llm_result["status"], "latency_ms": llm_latency, "message": llm_result.get("message", "")},
        "anythingllm": {"status": anythingllm_result["status"], "latency_ms": anythingllm_latency, "message": anythingllm_result.get("message", "")},
    }
