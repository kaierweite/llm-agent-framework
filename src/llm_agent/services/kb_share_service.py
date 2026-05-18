"""知识库分享服务：分享码生成、凭码访问、权限校验、访问留痕。"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from llm_agent.models.knowledge_base import KnowledgeBase
from llm_agent.models.knowledge_base_share import KnowledgeBaseShare, SHARE_CODE_TTL_DAYS
from llm_agent.models.knowledge_base_access_log import KnowledgeBaseAccessLog
from llm_agent.models.user import User


# ── 访问动作常量 ──────────────────────────────────────────
ACCESS_VIEW = "view"          # 查看知识库详情
ACCESS_QUERY = "query"        # 查询问答
ACCESS_DOWNLOAD = "download"  # 下载文档
ACCESS_SHARE = "share"        # 分享操作


class ShareError(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


# ── 分享码操作 ────────────────────────────────────────────

def generate_share_code(
    db: Session,
    kb_id: str,
    owner_id: str,
    permission: str = "read",
) -> KnowledgeBaseShare:
    """为知识库生成一个分享码。同一知识库可生成多个不同权限的分享码。"""
    kb = db.query(KnowledgeBase).filter(
        KnowledgeBase.id == kb_id,
        KnowledgeBase.owner_id == owner_id,
    ).first()
    if not kb:
        raise ShareError(40401, "知识库不存在或无权操作")

    share = KnowledgeBaseShare(
        knowledge_base_id=kb_id,
        shared_by_id=owner_id,
        permission=permission,
        expires_at=datetime.now(timezone.utc) + timedelta(days=SHARE_CODE_TTL_DAYS),
    )
    db.add(share)
    db.commit()
    db.refresh(share)
    return share


def revoke_share_code(
    db: Session,
    share_id: str,
    owner_id: str,
) -> bool:
    """吊销一个分享码（设为无效）。"""
    share = db.query(KnowledgeBaseShare).filter(
        KnowledgeBaseShare.id == share_id,
        KnowledgeBaseShare.shared_by_id == owner_id,
    ).first()
    if not share:
        return False

    share.is_active = False
    db.commit()
    return True


def list_share_codes(
    db: Session,
    kb_id: str,
    owner_id: str,
) -> list[dict]:
    """列出知识库的所有分享码。"""
    kb = db.query(KnowledgeBase).filter(
        KnowledgeBase.id == kb_id,
        KnowledgeBase.owner_id == owner_id,
    ).first()
    if not kb:
        raise ShareError(40401, "知识库不存在或无权操作")

    rows = (
        db.query(KnowledgeBaseShare)
        .filter(KnowledgeBaseShare.knowledge_base_id == kb_id)
        .order_by(desc(KnowledgeBaseShare.created_at))
        .all()
    )

    now = datetime.now(timezone.utc)
    return [
        {
            "id": s.id,
            "share_code": s.share_code,
            "permission": s.permission,
            "is_active": s.is_active,
            "is_expired": s.expires_at < now if s.expires_at else False,
            "expires_at": s.expires_at.isoformat() if s.expires_at else None,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in rows
    ]


def access_by_share_code(
    db: Session,
    share_code: str,
    user_id: str,
) -> Tuple[KnowledgeBaseShare, KnowledgeBase]:
    """凭分享码访问知识库。校验码有效性，返回 share 记录和知识库。"""
    code = share_code.strip().upper()

    share = db.query(KnowledgeBaseShare).filter(
        KnowledgeBaseShare.share_code == code,
    ).first()
    if not share:
        raise ShareError(40402, "分享码不存在")

    if not share.is_active:
        raise ShareError(40301, "分享码已吊销")

    now = datetime.now(timezone.utc)
    if share.expires_at and share.expires_at < now:
        raise ShareError(40302, "分享码已过期")

    kb = db.query(KnowledgeBase).filter(
        KnowledgeBase.id == share.knowledge_base_id,
    ).first()
    if not kb:
        raise ShareError(40403, "知识库已被删除")

    return share, kb


# ── 权限校验（兼容 owner + 分享码） ──────────────────────

def can_access(
    db: Session,
    kb_id: str,
    user_id: str,
) -> Optional[KnowledgeBaseShare]:
    """检查用户是否有权访问该知识库。
    - owner → 返回 None
    - 通过成员表 → 返回虚拟 share 对象（permission 来自成员表）
    - 通过分享码访问 → 返回对应的 share 记录（is_active=True）
    - 无权限 → 返回 None
    """
    from llm_agent.models.knowledge_base_member import KnowledgeBaseMember

    # Owner 直接放行
    kb = db.query(KnowledgeBase).filter(
        KnowledgeBase.id == kb_id,
        KnowledgeBase.owner_id == user_id,
    ).first()
    if kb:
        return None  # None 表示是 owner

    # 检查成员表
    member = db.query(KnowledgeBaseMember).filter(
        KnowledgeBaseMember.knowledge_base_id == kb_id,
        KnowledgeBaseMember.user_id == user_id,
    ).first()
    if member:
        # 构造一个虚拟 share 对象，复用 permission 字段
        virtual_share = KnowledgeBaseShare(
            knowledge_base_id=kb_id,
            shared_by_id=kb.owner_id if kb else user_id,
            permission=member.permission,
        )
        return virtual_share

    # 检查是否有有效的分享码（该用户曾通过某个分享码访问过）
    now = datetime.now(timezone.utc)
    active_share = db.query(KnowledgeBaseShare).filter(
        KnowledgeBaseShare.knowledge_base_id == kb_id,
        KnowledgeBaseShare.is_active == True,
        KnowledgeBaseShare.expires_at > now,
    ).first()
    if active_share:
        return active_share

    return None  # 没有活跃且未过期的分享码 = 不可访问


def get_accessible_knowledge_base(
    db: Session,
    kb_id: str,
    user_id: str,
) -> Optional[KnowledgeBase]:
    """获取用户可访问的知识库（owner、成员、或有活跃分享码）。"""
    from llm_agent.models.knowledge_base_member import KnowledgeBaseMember

    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        return None

    # Owner
    if kb.owner_id == user_id:
        return kb

    # 成员表
    member = db.query(KnowledgeBaseMember).filter(
        KnowledgeBaseMember.knowledge_base_id == kb_id,
        KnowledgeBaseMember.user_id == user_id,
    ).first()
    if member:
        return kb

    # 有活跃分享码的知识库，登录用户均可访问
    now = datetime.now(timezone.utc)
    active_share = db.query(KnowledgeBaseShare).filter(
        KnowledgeBaseShare.knowledge_base_id == kb_id,
        KnowledgeBaseShare.is_active == True,
        KnowledgeBaseShare.expires_at > now,
    ).first()
    if active_share:
        return kb

    return None


# ── 访问留痕 ──────────────────────────────────────────────

def log_access(
    db: Session,
    kb_id: str,
    user_id: str,
    action: str,
    detail: Optional[str] = None,
    ip_address: Optional[str] = None,
    share_code: Optional[str] = None,
) -> KnowledgeBaseAccessLog:
    """记录一次知识库访问，可选记录通过哪个分享码进入。"""
    entry = KnowledgeBaseAccessLog(
        knowledge_base_id=kb_id,
        user_id=user_id,
        action=action,
        detail=detail,
        share_code=share_code,
        ip_address=ip_address,
    )
    db.add(entry)
    db.commit()
    return entry


def list_access_logs(
    db: Session,
    kb_id: str,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[list, int]:
    """查询某个知识库的访问日志。"""
    total = (
        db.query(func.count(KnowledgeBaseAccessLog.id))
        .filter(KnowledgeBaseAccessLog.knowledge_base_id == kb_id)
        .scalar()
    )

    rows = (
        db.query(KnowledgeBaseAccessLog, User)
        .join(User, User.id == KnowledgeBaseAccessLog.user_id)
        .filter(KnowledgeBaseAccessLog.knowledge_base_id == kb_id)
        .order_by(desc(KnowledgeBaseAccessLog.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = []
    for log, user in rows:
        items.append({
            "id": log.id,
            "user_id": log.user_id,
            "email": user.email,
            "display_name": user.display_name,
            "action": log.action,
            "detail": log.detail,
            "share_code": log.share_code,
            "ip_address": log.ip_address,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        })

    return items, total
