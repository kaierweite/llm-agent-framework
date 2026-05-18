"""
管理后台服务 —— 用户管理、系统统计、系统配置（.env）。

连接测试与健康检查已拆分至 connection_test_service.py，
系统参数 CRUD 已拆分至 system_config_service.py。
本模块通过 re-export 保持向后兼容。
"""

import os
from datetime import datetime
from typing import Tuple, Optional

import bcrypt
from sqlalchemy import String, Text, DateTime, func, desc
from sqlalchemy.orm import Session, Mapped, mapped_column

from llm_agent import PROJECT_ROOT
from llm_agent.database import Base
from llm_agent.config import settings
from llm_agent.models.user import User
from llm_agent.models.knowledge_base import KnowledgeBase
from llm_agent.models.document import Document
from llm_agent.models.conversation import Conversation

# ── re-export：保持已有调用方不报错 ──────────────────────────────
from llm_agent.services.connection_test_service import (  # noqa: F401
    test_llm_connection,
    test_anythingllm_connection,
    get_health_check,
)
from llm_agent.services.system_config_service import (  # noqa: F401
    get_system_config as get_system_db_config,
    set_system_config,
    get_all_system_configs,
    batch_update_system_configs,
    get_user_preferences,
    update_user_preferences,
)

# ── DB 设置别名（API 层使用） ────────────────────────────────────
def get_system_settings(db: Session) -> dict:
    return get_all_system_configs(db)

def update_system_settings(db: Session, settings_dict: dict) -> int:
    return batch_update_system_configs(db, settings_dict)


class AdminError(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class _SystemSetting(Base):
    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# ── 用户管理 ─────────────────────────────────────────────────────


def _user_to_dict(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "role": user.role,
        "is_active": user.is_active,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }


def list_users(
    db: Session, page: int = 1, page_size: int = 20
) -> Tuple[list, int]:
    total = db.query(func.count(User.id)).scalar()

    rows = (
        db.query(User)
        .order_by(desc(User.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = [_user_to_dict(u) for u in rows]
    return items, total


def get_user(db: Session, user_id: str) -> Optional[dict]:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    return _user_to_dict(user)


def update_user_role(db: Session, user_id: str, role: str) -> Optional[dict]:
    if role not in ("admin", "member"):
        raise AdminError(40001, f"Invalid role '{role}', must be 'admin' or 'member'")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None

    user.role = role
    db.commit()
    db.refresh(user)
    return _user_to_dict(user)


def toggle_user_active(db: Session, user_id: str) -> Optional[dict]:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None

    user.is_active = not user.is_active
    db.commit()
    db.refresh(user)
    return _user_to_dict(user)


def reset_user_password(db: Session, user_id: str, new_password: str) -> Optional[dict]:
    if len(new_password) < 6:
        raise AdminError(40002, "密码长度不能少于6位")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None

    password_hash = bcrypt.hashpw(
        new_password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")
    user.password_hash = password_hash
    db.commit()
    db.refresh(user)
    return _user_to_dict(user)


def delete_user(db: Session, user_id: str) -> bool:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False

    db.delete(user)
    db.commit()
    return True


def update_user_status(db: Session, user_id: str, is_active: bool) -> Optional[User]:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    user.is_active = is_active
    db.commit()
    db.refresh(user)
    return user


# ── 系统统计 ─────────────────────────────────────────────────────


def get_system_stats(db: Session) -> dict:
    total_users = db.query(func.count(User.id)).scalar()
    active_users = (
        db.query(func.count(User.id))
        .filter(User.is_active == True)
        .scalar()
    )
    total_conversations = db.query(func.count(Conversation.id)).scalar()
    total_knowledge_bases = db.query(func.count(KnowledgeBase.id)).scalar()
    total_documents = db.query(func.count(Document.id)).scalar()

    return {
        "total_users": total_users,
        "active_users": active_users,
        "total_conversations": total_conversations,
        "total_knowledge_bases": total_knowledge_bases,
        "total_documents": total_documents,
    }


# ── 系统配置（.env 文件读写）─────────────────────────────────────


def _mask_key(key: str) -> str:
    if not key:
        return ""
    if len(key) <= 4:
        return key + "****"
    return key[:4] + "****"


def get_system_config() -> dict:
    return {
        "llm_base_url": settings.llm_base_url,
        "llm_model": settings.llm_model,
        "llm_api_key": _mask_key(settings.llm_api_key),
        "anythingllm_base_url": settings.anythingllm_base_url,
        "anythingllm_api_key": _mask_key(settings.anythingllm_api_key),
        "anythingllm_workspace_slug": settings.anythingllm_workspace_slug,
        "cors_origins": settings.cors_origins,
    }


_ENV_FILE = os.path.join(PROJECT_ROOT, ".env")
_WRITABLE_KEYS = {
    "llm_base_url", "llm_model", "llm_api_key",
    "anythingllm_base_url", "anythingllm_api_key", "anythingllm_workspace_slug",
}


def update_system_config(config_data: dict) -> dict:
    lines = []
    if os.path.exists(_ENV_FILE):
        with open(_ENV_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()

    key_to_line = {}
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            k = stripped.split("=", 1)[0].strip()
            key_to_line[k] = i

    for key, value in config_data.items():
        if key not in _WRITABLE_KEYS:
            continue
        env_key = key.upper()
        value_str = str(value)
        if env_key in key_to_line:
            lines[key_to_line[env_key]] = f"{env_key}={value_str}\n"
        else:
            lines.append(f"{env_key}={value_str}\n")

    with open(_ENV_FILE, "w", encoding="utf-8") as f:
        f.writelines(lines)

    os.environ["LLM_BASE_URL"] = config_data.get("llm_base_url", settings.llm_base_url)
    os.environ["LLM_MODEL"] = config_data.get("llm_model", settings.llm_model)
    os.environ["LLM_API_KEY"] = config_data.get("llm_api_key", settings.llm_api_key)
    os.environ["ANYTHINGLLM_BASE_URL"] = config_data.get("anythingllm_base_url", settings.anythingllm_base_url)
    os.environ["ANYTHINGLLM_API_KEY"] = config_data.get("anythingllm_api_key", settings.anythingllm_api_key)

    # 同步更新 settings 单例，避免运行时读到旧值
    if "llm_base_url" in config_data:
        settings.llm_base_url = config_data["llm_base_url"]
    if "llm_model" in config_data:
        settings.llm_model = config_data["llm_model"]
    if "llm_api_key" in config_data:
        settings.llm_api_key = config_data["llm_api_key"]
    if "anythingllm_base_url" in config_data:
        settings.anythingllm_base_url = config_data["anythingllm_base_url"]
    if "anythingllm_api_key" in config_data:
        settings.anythingllm_api_key = config_data["anythingllm_api_key"]
    if "anythingllm_workspace_slug" in config_data:
        settings.anythingllm_workspace_slug = config_data["anythingllm_workspace_slug"]

    return get_system_config()
