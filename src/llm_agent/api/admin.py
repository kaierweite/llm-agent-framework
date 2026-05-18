from typing import Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from llm_agent.database import get_db
from llm_agent.middleware.auth import require_admin, require_admin_or_auditor
from llm_agent.models.user import User
from llm_agent.services import admin_service, skill_service
from llm_agent.services.admin_service import AdminError
from llm_agent.services.skill_service import SkillError
from llm_agent.services.audit_service import (
    log_action, list_audit_logs, get_audit_stats, cleanup_old_logs, export_audit_logs,
    ACTION_ADMIN_USER_ROLE, ACTION_ADMIN_USER_STATUS, ACTION_ADMIN_USER_DELETE,
    ACTION_ADMIN_USER_PASSWORD_RESET, ACTION_ADMIN_CONFIG_UPDATE, ACTION_ADMIN_SETTINGS_UPDATE,
)


class AdminUserRole(BaseModel):
    role: str


class AdminResetPassword(BaseModel):
    new_password: str


class AdminSettingsUpdate(BaseModel):
    settings: dict[str, str]


class AdminUserStatus(BaseModel):
    is_active: bool


class AdminConfigUpdate(BaseModel):
    llm_base_url: Optional[str] = None
    llm_model: Optional[str] = None
    llm_api_key: Optional[str] = None
    anythingllm_base_url: Optional[str] = None
    anythingllm_api_key: Optional[str] = None


class AdminTestLLM(BaseModel):
    base_url: str
    api_key: str
    model: str


class AdminTestAnythingLLM(BaseModel):
    base_url: str
    api_key: str


class AdminSkillCreate(BaseModel):
    name: str
    display_name: str
    description: Optional[str] = None
    version: Optional[str] = "1.0.0"
    author: Optional[str] = None
    config_schema: Optional[str] = None


class AdminSkillUpdate(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    version: Optional[str] = None
    author: Optional[str] = None
    config_schema: Optional[str] = None
    is_enabled: Optional[bool] = None


router = APIRouter(prefix="/api/admin", tags=["管理后台"])


def _user_to_dict(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "role": user.role,
        "department_id": user.department_id,
        "is_active": user.is_active,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }


@router.get("/users")
def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
        current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    items, total = admin_service.list_users(db, page=page, page_size=page_size)
    return {
        "code": 0,
        "message": "success",
        "data": {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        },
    }


@router.get("/users/{user_id}")
def get_user(
    user_id: str,
        current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    data = admin_service.get_user(db, user_id)
    if not data:
        raise HTTPException(status_code=404, detail={"code": 40401, "message": "User not found"})
    return {"code": 0, "message": "success", "data": data}


@router.put("/users/{user_id}/role")
def update_user_role(
    user_id: str,
    body: AdminUserRole,
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail={"code": 40001, "message": "不能修改自己的角色"})
    target_user = db.query(User).filter(User.id == user_id).first()
    old_role = target_user.role if target_user else "?"
    try:
        data = admin_service.update_user_role(db, user_id, body.role)
    except AdminError as e:
        raise HTTPException(status_code=400, detail={"code": e.code, "message": e.message})
    if not data:
        raise HTTPException(status_code=404, detail={"code": 40401, "message": "User not found"})
    log_action(db, ACTION_ADMIN_USER_ROLE, user_id=current_user.id, user_email=current_user.email,
               resource_type="user", resource_id=user_id,
               detail=f"角色从 {old_role} 变更为 {body.role}",
               ip_address=request.client.host if request.client else None)
    return {"code": 0, "message": "success", "data": data}


@router.put("/users/{user_id}/toggle-active")
def toggle_user_active(
    user_id: str,
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail={"code": 40001, "message": "不能禁用自己的账号"})
    data = admin_service.toggle_user_active(db, user_id)
    if not data:
        raise HTTPException(status_code=404, detail={"code": 40401, "message": "User not found"})
    log_action(db, ACTION_ADMIN_USER_STATUS, user_id=current_user.id, user_email=current_user.email,
               resource_type="user", resource_id=user_id,
               detail=f"状态变更为 {'启用' if data.get('is_active') else '禁用'}",
               ip_address=request.client.host if request.client else None)
    return {"code": 0, "message": "success", "data": data}


@router.post("/users/{user_id}/reset-password")
def reset_user_password(
    user_id: str,
    body: AdminResetPassword,
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    data = admin_service.reset_user_password(db, user_id, body.new_password)
    if not data:
        raise HTTPException(status_code=404, detail={"code": 40401, "message": "User not found"})
    log_action(db, ACTION_ADMIN_USER_PASSWORD_RESET, user_id=current_user.id, user_email=current_user.email,
               resource_type="user", resource_id=user_id, detail="管理员重置密码",
               ip_address=request.client.host if request.client else None)
    return {"code": 0, "message": "success", "data": data}


@router.delete("/users/{user_id}")
def delete_user(
    user_id: str,
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail={"code": 40001, "message": "不能删除自己的账号"})
    target_user = db.query(User).filter(User.id == user_id).first()
    target_email = target_user.email if target_user else user_id
    deleted = admin_service.delete_user(db, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail={"code": 40401, "message": "User not found"})
    log_action(db, ACTION_ADMIN_USER_DELETE, user_id=current_user.id, user_email=current_user.email,
               resource_type="user", resource_id=user_id,
               detail=f"删除用户: {target_email}",
               ip_address=request.client.host if request.client else None)
    return {"code": 0, "message": "User deleted", "data": None}


@router.get("/stats")
def get_system_stats(
        current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    data = admin_service.get_system_stats(db)
    return {"code": 0, "message": "success", "data": data}


@router.get("/settings")
def get_system_settings(
        current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    data = admin_service.get_system_settings(db)
    return {"code": 0, "message": "success", "data": data}


@router.put("/settings")
def update_system_settings(
    body: AdminSettingsUpdate,
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    data = admin_service.update_system_settings(db, body.settings)
    log_action(db, ACTION_ADMIN_SETTINGS_UPDATE, user_id=current_user.id, user_email=current_user.email,
               resource_type="system", detail=f"更新系统设置: {', '.join(body.settings.keys())}",
               ip_address=request.client.host if request.client else None)
    return {"code": 0, "message": "success", "data": data}


@router.get("/config")
def get_system_config(
        current_user: User = Depends(require_admin),
):
    data = admin_service.get_system_config()
    return {"code": 0, "message": "success", "data": data}


@router.put("/config")
def update_system_config(
    body: AdminConfigUpdate,
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    config_data = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None}
    data = admin_service.update_system_config(config_data)
    log_action(db, ACTION_ADMIN_CONFIG_UPDATE, user_id=current_user.id, user_email=current_user.email,
               resource_type="system", detail=f"更新模型配置: {', '.join(config_data.keys())}",
               ip_address=request.client.host if request.client else None)
    return {"code": 0, "message": "success", "data": data}


@router.post("/config/test-llm")
def test_llm_connection(
    body: AdminTestLLM,
        current_user: User = Depends(require_admin),
):
    data = admin_service.test_llm_connection(body.base_url, body.api_key, body.model)
    return {"code": 0, "message": "success", "data": data}


@router.post("/config/test-anythingllm")
def test_anythingllm_connection(
    body: AdminTestAnythingLLM,
        current_user: User = Depends(require_admin),
):
    data = admin_service.test_anythingllm_connection(body.base_url, body.api_key)
    return {"code": 0, "message": "success", "data": data}


@router.get("/health")
def health_check(
        current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    data = admin_service.get_health_check(db)
    return {"code": 0, "message": "success", "data": data}


@router.put("/users/{user_id}/status")
def update_user_status(
    user_id: str,
    body: AdminUserStatus,
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail={"code": 40001, "message": "不能修改自己的状态"})
    data = admin_service.update_user_status(db, user_id, body.is_active)
    if not data:
        raise HTTPException(status_code=404, detail={"code": 40401, "message": "User not found"})
    log_action(db, ACTION_ADMIN_USER_STATUS, user_id=current_user.id, user_email=current_user.email,
               resource_type="user", resource_id=user_id,
               detail=f"状态变更为 {'启用' if body.is_active else '禁用'}",
               ip_address=request.client.host if request.client else None)
    return {"code": 0, "message": "success", "data": _user_to_dict(data)}


@router.get("/skills")
def list_skills(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
        current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    items, total = skill_service.list_skills(db, page=page, page_size=page_size)
    return {
        "code": 0,
        "message": "success",
        "data": {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        },
    }


@router.get("/skills/{skill_id}")
def get_skill(
    skill_id: str,
        current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    data = skill_service.get_skill(db, skill_id)
    if not data:
        raise HTTPException(status_code=404, detail={"code": 40401, "message": "Skill not found"})
    return {"code": 0, "message": "success", "data": data}


@router.post("/skills", status_code=201)
def create_skill(
    body: AdminSkillCreate,
        current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        data = skill_service.create_skill(
            db,
            name=body.name,
            display_name=body.display_name,
            description=body.description,
            version=body.version,
            author=body.author,
            config_schema=body.config_schema,
        )
    except SkillError as e:
        raise HTTPException(status_code=409, detail={"code": e.code, "message": e.message})
    return {"code": 0, "message": "success", "data": data}


@router.put("/skills/{skill_id}")
def update_skill(
    skill_id: str,
    body: AdminSkillUpdate,
        current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    kwargs = {k: v for k, v in body.model_dump(exclude_unset=True).items()}
    data = skill_service.update_skill(db, skill_id, **kwargs)
    if not data:
        raise HTTPException(status_code=404, detail={"code": 40401, "message": "Skill not found"})
    return {"code": 0, "message": "success", "data": data}


@router.delete("/skills/{skill_id}")
def delete_skill(
    skill_id: str,
        current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    deleted = skill_service.delete_skill(db, skill_id)
    if not deleted:
        raise HTTPException(status_code=404, detail={"code": 40401, "message": "Skill not found"})
    return {"code": 0, "message": "Skill deleted", "data": None}


@router.put("/skills/{skill_id}/toggle-enabled")
def toggle_skill_enabled(
    skill_id: str,
        current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    data = skill_service.toggle_skill_enabled(db, skill_id)
    if not data:
        raise HTTPException(status_code=404, detail={"code": 40401, "message": "Skill not found"})
    return {"code": 0, "message": "success", "data": data}




# ── 审计日志统计 ──────────────────────────────────────────

@router.get("/audit-logs/stats")
def get_audit_logs_stats(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(require_admin_or_auditor),
    db: Session = Depends(get_db),
):
    data = get_audit_stats(db, days=days)
    return {"code": 0, "message": "success", "data": data}


# ── 审计日志导出 ──────────────────────────────────────────

@router.get("/audit-logs/export")
def export_audit_logs_endpoint(
    start_time: Optional[str] = Query(None),
    end_time: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    current_user: User = Depends(require_admin_or_auditor),
    db: Session = Depends(get_db),
):
    from datetime import datetime as dt
    start = dt.fromisoformat(start_time) if start_time else None
    end = dt.fromisoformat(end_time) if end_time else None
    items = export_audit_logs(db, start_time=start, end_time=end, action=action)
    return {"code": 0, "message": "success", "data": {"items": items, "total": len(items)}}


# ── 审计日志清理 ──────────────────────────────────────────

@router.post("/audit-logs/cleanup")
def cleanup_audit_logs(
    keep_days: int = Query(90, ge=7, le=365),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    deleted = cleanup_old_logs(db, keep_days=keep_days)
    log_action(db, "admin.audit_cleanup", user_id=current_user.id, user_email=current_user.email,
               resource_type="system", detail=f"清理 {keep_days} 天前的审计日志，删除 {deleted} 条")
    return {"code": 0, "message": "success", "data": {"deleted": deleted, "keep_days": keep_days}}

# ── 审计日志（管理员 + 审计员可访问） ──────────────────────

@router.get("/audit-logs")
def get_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    action: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    start_time: Optional[str] = Query(None),
    end_time: Optional[str] = Query(None),
    current_user: User = Depends(require_admin_or_auditor),
    db: Session = Depends(get_db),
):
    from datetime import datetime as dt
    start = dt.fromisoformat(start_time) if start_time else None
    end = dt.fromisoformat(end_time) if end_time else None
    items, total = list_audit_logs(
        db, page=page, page_size=page_size, action=action, user_id=user_id,
        resource_type=resource_type, keyword=keyword, start_time=start, end_time=end,
    )
    return {
        "code": 0,
        "message": "success",
        "data": {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        },
    }
