"""
审计日志服务 — 行业标准实现

功能：
- log_action(): 核心日志写入函数
- @audit_log() 装饰器：减少路由样板代码，自动提取请求上下文
- list_audit_logs(): 分页查询，支持多维筛选
- cleanup_old_logs(): 自动清理过期日志（保留策略）
- 敏感数据脱敏：detail 中的密码、token 等自动替换

动作常量命名规范：
- {模块}.{操作}，如 user.login, knowledge_base.create, conversation.delete
- 管理员操作前缀 admin., 如 admin.user_role_change
- 系统操作前缀 system., 如 system.config_update
"""

import re
import json
import functools
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple, Callable

from fastapi import Request
from sqlalchemy import desc, func, text
from sqlalchemy.orm import Session

from llm_agent.models.audit_log import AuditLog


# ── 动作常量 ──────────────────────────────────────────────
# 认证
ACTION_USER_LOGIN = "user.login"
ACTION_USER_REGISTER = "user.register"
ACTION_USER_LOGOUT = "user.logout"
ACTION_USER_PASSWORD_CHANGE = "user.password_change"

# 管理员操作
ACTION_ADMIN_USER_ROLE = "admin.user_role_change"
ACTION_ADMIN_USER_STATUS = "admin.user_status_change"
ACTION_ADMIN_USER_DELETE = "admin.user_delete"
ACTION_ADMIN_USER_PASSWORD_RESET = "admin.user_password_reset"
ACTION_ADMIN_CONFIG_UPDATE = "admin.config_update"
ACTION_ADMIN_SETTINGS_UPDATE = "admin.settings_update"

# 知识库
ACTION_KB_CREATE = "knowledge_base.create"
ACTION_KB_DELETE = "knowledge_base.delete"
ACTION_KB_UPDATE = "knowledge_base.update"
ACTION_KB_SHARE = "knowledge_base.share"

# 文档
ACTION_DOC_UPLOAD = "document.upload"
ACTION_DOC_DELETE = "document.delete"

# 对话
ACTION_CONVERSATION_CREATE = "conversation.create"
ACTION_CONVERSATION_DELETE = "conversation.delete"
ACTION_CONVERSATION_RENAME = "conversation.rename"

# 消息反馈
ACTION_MESSAGE_FEEDBACK = "message.feedback"

# 知识库访问（独立表，但也记录到审计日志）
ACTION_KB_ACCESS = "knowledge_base.access"


# ── 敏感数据脱敏 ──────────────────────────────────────────
_SENSITIVE_PATTERNS = [
    (re.compile(r'"password"\s*:\s*"[^"]*"', re.IGNORECASE), '"password": "***"'),
    (re.compile(r'"old_password"\s*:\s*"[^"]*"', re.IGNORECASE), '"old_password": "***"'),
    (re.compile(r'"new_password"\s*:\s*"[^"]*"', re.IGNORECASE), '"new_password": "***"'),
    (re.compile(r'"api_key"\s*:\s*"[^"]*"', re.IGNORECASE), '"api_key": "***"'),
    (re.compile(r'"token"\s*:\s*"[^"]*"', re.IGNORECASE), '"token": "***"'),
    (re.compile(r'Bearer\s+\S+', re.IGNORECASE), 'Bearer ***'),
]


def _sanitize_detail(detail: str) -> str:
    """对 detail 字符串中的敏感信息进行脱敏"""
    if not detail:
        return detail
    for pattern, replacement in _SENSITIVE_PATTERNS:
        detail = pattern.sub(replacement, detail)
    return detail


# ── 核心日志写入 ──────────────────────────────────────────
def log_action(
    db: Session,
    action: str,
    *,
    user_id: Optional[str] = None,
    user_email: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    detail: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> AuditLog:
    """
    写入一条审计日志。

    Args:
        db: 数据库会话
        action: 操作类型（使用 ACTION_* 常量）
        user_id: 操作用户 ID
        user_email: 操作用户邮箱
        resource_type: 资源类型（user/system/knowledge_base/document/conversation）
        resource_id: 资源 ID
        detail: 操作详情（会自动脱敏）
        ip_address: 客户端 IP

    Returns:
        创建的 AuditLog 实例
    """
    # 脱敏处理
    sanitized_detail = _sanitize_detail(detail) if detail else None

    entry = AuditLog(
        user_id=user_id,
        user_email=user_email,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        detail=sanitized_detail,
        ip_address=ip_address,
    )
    db.add(entry)
    db.commit()
    return entry


# ── 装饰器：自动审计日志 ──────────────────────────────────
def audit_log(
    action: str,
    resource_type: Optional[str] = None,
    get_resource_id: Optional[Callable] = None,
    get_detail: Optional[Callable] = None,
):
    """
    装饰器：自动为路由函数添加审计日志。

    用法：
        @router.post("/knowledge/bases")
        @audit_log(ACTION_KB_CREATE, resource_type="knowledge_base",
                   get_detail=lambda body, **kw: f"创建知识库: {body.name}")
        def create_kb(
            body: CreateKBRequest,
            request: Request,
            current_user: User = Depends(get_current_user),
            db: Session = Depends(get_db),
        ):
            ...

    参数：
        action: 操作类型（使用 ACTION_* 常量）
        resource_type: 资源类型
        get_resource_id: 从函数参数中提取资源 ID 的回调
            签名: (body=None, result=None, **kwargs) -> Optional[str]
        get_detail: 从函数参数中生成 detail 的回调
            签名: (body=None, result=None, **kwargs) -> Optional[str]
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # 执行原始函数
            result = func(*args, **kwargs)

            # 如果是协程，等待它完成
            import asyncio
            if asyncio.iscoroutine(result):
                result = await result

            # 从 kwargs 中提取上下文
            request: Optional[Request] = kwargs.get("request")
            current_user = kwargs.get("current_user")
            db: Optional[Session] = kwargs.get("db")
            body = kwargs.get("body")

            if not db:
                return result

            # 提取用户信息
            user_id = None
            user_email = None
            if current_user:
                user_id = str(current_user.id) if hasattr(current_user, "id") else None
                user_email = current_user.email if hasattr(current_user, "email") else None

            # 提取 IP
            ip_address = None
            if request and request.client:
                ip_address = request.client.host

            # 提取资源 ID
            resource_id = None
            if get_resource_id:
                try:
                    resource_id = get_resource_id(body=body, result=result, **kwargs)
                except Exception:
                    pass

            # 生成 detail
            detail = None
            if get_detail:
                try:
                    detail = get_detail(body=body, result=result, **kwargs)
                except Exception:
                    pass

            # 写入日志
            log_action(
                db,
                action,
                user_id=user_id,
                user_email=user_email,
                resource_type=resource_type,
                resource_id=str(resource_id) if resource_id else None,
                detail=detail,
                ip_address=ip_address,
            )

            return result

        return wrapper
    return decorator


# ── 查询审计日志 ──────────────────────────────────────────
def list_audit_logs(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 20,
    action: Optional[str] = None,
    user_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    keyword: Optional[str] = None,
) -> Tuple[list[dict], int]:
    """
    查询审计日志，支持多维筛选。

    Args:
        db: 数据库会话
        page: 页码（从 1 开始）
        page_size: 每页条数
        action: 按操作类型筛选
        user_id: 按用户 ID 筛选
        resource_type: 按资源类型筛选
        start_time: 开始时间
        end_time: 结束时间
        keyword: 搜索关键词（匹配 detail 字段）

    Returns:
        (日志列表, 总数)
    """
    query = db.query(AuditLog)

    if action:
        query = query.filter(AuditLog.action == action)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
    if start_time:
        query = query.filter(AuditLog.created_at >= start_time)
    if end_time:
        query = query.filter(AuditLog.created_at <= end_time)
    if keyword:
        query = query.filter(AuditLog.detail.ilike(f"%{keyword}%"))

    total = query.count()
    items = (
        query.order_by(desc(AuditLog.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    result = [
        {
            "id": log.id,
            "user_id": log.user_id,
            "user_email": log.user_email,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "detail": log.detail,
            "ip_address": log.ip_address,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in items
    ]
    return result, total


# ── 日志统计 ──────────────────────────────────────────────
def get_audit_stats(
    db: Session,
    *,
    days: int = 30,
) -> dict:
    """
    获取审计日志统计信息。

    Returns:
        {
            "total": 总日志数,
            "by_action": {"action": count, ...},
            "by_user": {"user_email": count, ...},
            "by_day": [{"date": "2026-05-14", "count": 42}, ...],
            "error_count": 错误请求数（status >= 400 的）
        }
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)

    # 总数
    total = db.query(func.count(AuditLog.id)).filter(
        AuditLog.created_at >= since
    ).scalar()

    # 按操作类型统计
    by_action_rows = (
        db.query(AuditLog.action, func.count(AuditLog.id))
        .filter(AuditLog.created_at >= since)
        .group_by(AuditLog.action)
        .all()
    )
    by_action = {row[0]: row[1] for row in by_action_rows}

    # 按用户统计（Top 10）
    by_user_rows = (
        db.query(AuditLog.user_email, func.count(AuditLog.id))
        .filter(AuditLog.created_at >= since, AuditLog.user_email.isnot(None))
        .group_by(AuditLog.user_email)
        .order_by(desc(func.count(AuditLog.id)))
        .limit(10)
        .all()
    )
    by_user = {row[0]: row[1] for row in by_user_rows}

    # 按天统计
    by_day_rows = (
        db.query(
            func.date(AuditLog.created_at).label("date"),
            func.count(AuditLog.id),
        )
        .filter(AuditLog.created_at >= since)
        .group_by(func.date(AuditLog.created_at))
        .order_by(func.date(AuditLog.created_at))
        .all()
    )
    by_day = [{"date": str(row[0]), "count": row[1]} for row in by_day_rows]

    return {
        "total": total,
        "by_action": by_action,
        "by_user": by_user,
        "by_day": by_day,
    }


# ── 日志清理（保留策略） ──────────────────────────────────
def cleanup_old_logs(
    db: Session,
    *,
    keep_days: int = 90,
    dry_run: bool = False,
) -> int:
    """
    清理过期审计日志。

    Args:
        db: 数据库会话
        keep_days: 保留天数（默认 90 天）
        dry_run: 仅返回将删除的数量，不实际删除

    Returns:
        将删除的日志数量
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=keep_days)

    count = db.query(func.count(AuditLog.id)).filter(
        AuditLog.created_at < cutoff
    ).scalar()

    if not dry_run and count > 0:
        db.query(AuditLog).filter(AuditLog.created_at < cutoff).delete()
        db.commit()

    return count


# ── 导出审计日志（CSV 格式） ──────────────────────────────
def export_audit_logs(
    db: Session,
    *,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    action: Optional[str] = None,
) -> list[dict]:
    """
    导出审计日志（用于合规审计）。

    Returns:
        日志列表（最多 10000 条）
    """
    query = db.query(AuditLog)

    if action:
        query = query.filter(AuditLog.action == action)
    if start_time:
        query = query.filter(AuditLog.created_at >= start_time)
    if end_time:
        query = query.filter(AuditLog.created_at <= end_time)

    items = (
        query.order_by(desc(AuditLog.created_at))
        .limit(10000)
        .all()
    )

    return [
        {
            "id": log.id,
            "timestamp": log.created_at.isoformat() if log.created_at else None,
            "user_id": log.user_id,
            "user_email": log.user_email,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "detail": log.detail,
            "ip_address": log.ip_address,
        }
        for log in items
    ]
