from pydantic_settings import BaseSettings
from pydantic import model_validator
from typing import List
import os
import secrets

from llm_agent import PROJECT_ROOT


class Settings(BaseSettings):
    llm_base_url: str = "http://localhost:1234/v1"
    llm_model: str = "qwen/qwen3.5-9b"
    llm_api_key: str = "EMPTY"

    @model_validator(mode="after")
    def validate_llm_api_key(self):
        if not self.llm_api_key or not self.llm_api_key.strip():
            raise ValueError(
                "llm_api_key 未设置。请在 .env 文件或环境变量中设置 LLM_API_KEY。"
            )
        return self

    @model_validator(mode="after")
    def validate_jwt_secret(self):
        if not self.jwt_secret:
            self.jwt_secret = secrets.token_hex(32)
            print("[config] WARNING: JWT_SECRET 未设置，已自动生成随机密钥。重启后所有 token 将失效。请在 .env 中设置 JWT_SECRET。")
        return self

    @model_validator(mode="after")
    def validate_admin_credentials(self):
        if not self.admin_email or not self.admin_password:
            print("[config] WARNING: ADMIN_EMAIL 或 ADMIN_PASSWORD 未设置，跳过管理员种子创建。")
        return self

    anythingllm_api_key: str = ""
    anythingllm_workspace_slug: str = "AI"
    anythingllm_base_url: str = "http://localhost:3001"
    anythingllm_chat_provider: str = "lmstudio"
    anythingllm_chat_model: str = "qwen/qwen3.5-9b"

    database_url: str = "postgresql://postgres:postgres@localhost:5432/llm_agent"

    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    admin_email: str = ""
    admin_password: str = ""

    upload_dir: str = os.path.join(PROJECT_ROOT, "uploads")
    max_upload_size_mb: int = 50

    log_file_path: str = os.path.join(PROJECT_ROOT, "logs", "chat.log")

    redis_url: str = "redis://localhost:6379/0"

    context_max_chars: int = 4000

    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: List[str] = ["http://localhost:5173"]

    model_config = {
        "env_file": os.path.join(PROJECT_ROOT, ".env"),
        "env_file_encoding": "utf-8",
    }


settings = Settings()
