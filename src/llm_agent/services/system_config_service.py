"""
系统配置服务 —— 系统参数的读写与批量更新。
"""

import json
from typing import Optional

from sqlalchemy.orm import Session

# 延迟导入避免循环依赖
def _get_admin_module():
    from llm_agent.services.admin_service import AdminError, _SystemSetting
    return AdminError, _SystemSetting


def get_system_config(db: Session, key: str) -> Optional[str]:
    _, _SystemSetting = _get_admin_module()
    setting = db.query(_SystemSetting).filter(_SystemSetting.key == key).first()
    if not setting:
        return None
    return setting.value


def set_system_config(db: Session, key: str, value: str, description: str = None) -> None:
    _, _SystemSetting = _get_admin_module()
    setting = db.query(_SystemSetting).filter(_SystemSetting.key == key).first()
    if setting:
        setting.value = value
        if description:
            setting.description = description
    else:
        setting = _SystemSetting(key=key, value=value, description=description)
        db.add(setting)
    db.commit()


def get_all_system_configs(db: Session) -> dict:
    _, _SystemSetting = _get_admin_module()
    settings = db.query(_SystemSetting).all()
    return {s.key: {"value": s.value, "description": s.description} for s in settings}


def batch_update_system_configs(db: Session, updates: dict) -> int:
    count = 0
    for key, value in updates.items():
        if isinstance(value, dict):
            val = value.get("value", "")
            desc = value.get("description")
        else:
            val = str(value)
            desc = None
        set_system_config(db, key, val, desc)
        count += 1
    return count


def get_user_preferences(db: Session, user_id: int) -> dict:
    raw = get_system_config(db, f"user_prefs_{user_id}")
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}


def update_user_preferences(db: Session, user_id: int, prefs: dict) -> None:
    existing = get_user_preferences(db, user_id)
    existing.update(prefs)
    set_system_config(db, f"user_prefs_{user_id}", json.dumps(existing, ensure_ascii=False))
