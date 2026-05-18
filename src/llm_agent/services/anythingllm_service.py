import os
import uuid
import threading
from typing import Optional

import httpx

from llm_agent.config import settings


class AnythingLLMError(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


# ── httpx 连接池（全局复用，线程安全） ──────────────────────────
_client: Optional[httpx.Client] = None
_client_lock = threading.Lock()


def _get_client() -> httpx.Client:
    global _client
    if _client is None or _client.is_closed:
        with _client_lock:
            if _client is None or _client.is_closed:
                _client = httpx.Client(
                    base_url=settings.anythingllm_base_url.rstrip("/"),
                    timeout=httpx.Timeout(connect=10, read=180, write=10, pool=10),
                    limits=httpx.Limits(
                        max_connections=20,
                        max_keepalive_connections=10,
                        keepalive_expiry=30,
                    ),
                                        headers={
                        "Authorization": f"Bearer {settings.anythingllm_api_key}",
                        "Accept": "application/json",
                    },
                )
    return _client


def _request(method: str, path: str, data: dict | None = None, timeout: int = 180) -> dict:
    client = _get_client()
    try:
        if data is not None:
            resp = client.request(method, path, json=data, timeout=timeout)
        else:
            resp = client.request(method, path, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as e:
        detail = e.response.text[:500] if e.response else ""
        raise AnythingLLMError(e.response.status_code, f"AnythingLLM API error {e.response.status_code}: {detail}") from e
    except httpx.ConnectError as e:
        raise AnythingLLMError(502, f"AnythingLLM connection failed: {e}") from e
    except Exception as e:
        raise AnythingLLMError(500, f"AnythingLLM request failed: {e}") from e


def create_workspace(name: str, description: str = "") -> dict:
    resp = _request("POST", "/api/v1/workspace/new", {"name": name})
    if "workspace" not in resp:
        raise AnythingLLMError(500, f"Unexpected response: {resp}")
    return resp["workspace"]


def delete_workspace(workspace_slug: str) -> bool:
    _request("DELETE", f"/api/v1/workspace/{workspace_slug}")
    return True


def upload_document(workspace_slug: str, file_path: str) -> dict:
    """上传文档到 AnythingLLM（使用 httpx multipart 上传）。"""
    client = _get_client()
    filename = os.path.basename(file_path)
    url = "/api/v1/document/upload"

    try:
        with open(file_path, "rb") as f:
            resp = client.post(
                url,
                files={"file": (filename, f, "application/octet-stream")},
                headers={"Authorization": f"Bearer {settings.anythingllm_api_key}"},
                timeout=120,
            )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as e:
        detail = e.response.text[:500] if e.response else ""
        raise AnythingLLMError(e.response.status_code, f"Upload failed {e.response.status_code}: {detail}") from e
    except httpx.ConnectError as e:
        raise AnythingLLMError(502, f"Upload connection failed: {e}") from e
    except Exception as e:
        raise AnythingLLMError(500, f"Upload failed: {e}") from e


def move_document_to_workspace(workspace_slug: str, doc_location: str) -> dict:
    resp = _request(
        "POST",
        f"/api/v1/workspace/{workspace_slug}/update-embeddings",
        {"adds": [doc_location], "deletes": []},
    )
    return resp


def delete_document(doc_location: str) -> bool:
    _request("DELETE", f"/api/v1/document/{doc_location}")
    return True


def query_workspace(workspace_slug: str, message: str) -> str:
    original_error = None
    try:
        resp = _request(
            "POST",
            f"/api/v1/workspace/{workspace_slug}/chat",
            {"message": message, "mode": "query", "enable_thinking": False},
        )
        if "textResponse" in resp:
            return resp["textResponse"]
        if "response" in resp:
            return resp["response"]
        raise AnythingLLMError(500, f"Unexpected chat response: {resp}")
    except AnythingLLMError as e:
        original_error = e

    # 查询失败时，尝试修复 workspace 聊天设置后重试一次
    try:
        update_workspace_chat_settings(
            workspace_slug,
            chat_provider=settings.anythingllm_chat_provider,
            chat_model=settings.anythingllm_chat_model,
        )
        resp = _request(
            "POST",
            f"/api/v1/workspace/{workspace_slug}/chat",
            {"message": message, "mode": "query", "enable_thinking": False},
        )
        if "textResponse" in resp:
            return resp["textResponse"]
        if "response" in resp:
            return resp["response"]
        raise AnythingLLMError(500, f"Unexpected chat response after retry: {resp}")
    except AnythingLLMError:
        # 重试也失败，抛出原始错误
        raise original_error


def update_workspace_chat_settings(
    workspace_slug: str,
    chat_provider: str = "lmstudio",
    chat_model: str = "",
) -> dict:
    """更新 AnythingLLM workspace 的聊天设置（LLM 提供者和模型）。"""
    payload = {"chatProvider": chat_provider}
    if chat_model:
        payload["chatModel"] = chat_model
    resp = _request("POST", f"/api/v1/workspace/{workspace_slug}/update", payload)
    return resp.get("workspace", resp)


def get_workspace_documents(workspace_slug: str) -> list:
    resp = _request("GET", f"/api/v1/workspace/{workspace_slug}")
    workspace_data = resp.get("workspace", [])
    if isinstance(workspace_data, list) and workspace_data:
        return workspace_data[0].get("documents", [])
    if isinstance(workspace_data, dict):
        return workspace_data.get("documents", [])
    return []
