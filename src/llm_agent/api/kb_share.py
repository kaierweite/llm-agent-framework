"""知识库分享 API：生成分享码、凭码访问、吊销、查看分享码、访问日志。"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from llm_agent.database import get_db
from llm_agent.middleware.auth import get_current_user
from llm_agent.models.user import User
from llm_agent.services import kb_share_service
from llm_agent.services.kb_share_service import ShareError
from llm_agent.services.audit_service import (
    log_action,
    ACTION_KB_SHARE,
)

router = APIRouter(prefix="/api/knowledge", tags=["知识库分享"])


# ── 请求体 ────────────────────────────────────────────────

class GenerateCodeRequest(BaseModel):
    permission: str = "read"  # read | query


class AccessByCodeRequest(BaseModel):
    share_code: str


# ── 分享码操作 ────────────────────────────────────────────

@router.post("/bases/{kb_id}/share-code", status_code=201)
def generate_share_code(
    kb_id: str,
    body: GenerateCodeRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """为知识库生成一个分享码。"""
    try:
        share = kb_share_service.generate_share_code(
            db, kb_id, current_user.id, body.permission,
        )
    except ShareError as e:
        raise HTTPException(
            status_code=404 if e.code == 40401 else 400,
            detail={"code": e.code, "message": e.message},
        )
    log_action(
        db, ACTION_KB_SHARE,
        user_id=current_user.id, user_email=current_user.email,
        resource_type="knowledge_base", resource_id=kb_id,
        detail=f"生成分享码: {share.share_code} (权限: {share.permission})",
        ip_address=request.client.host if request.client else None,
    )
    return {
        "code": 0,
        "message": "success",
        "data": {
            "id": share.id,
            "share_code": share.share_code,
            "permission": share.permission,
            "is_active": share.is_active,
            "created_at": share.created_at,
        },
    }


@router.delete("/share-codes/{share_id}")
def revoke_share_code(
    share_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """吊销一个分享码。"""
    ok = kb_share_service.revoke_share_code(db, share_id, current_user.id)
    if not ok:
        raise HTTPException(
            status_code=404,
            detail={"code": 40401, "message": "分享码不存在或无权操作"},
        )
    return {"code": 0, "message": "分享码已吊销", "data": None}


@router.get("/bases/{kb_id}/share-codes")
def list_share_codes(
    kb_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """列出知识库的所有分享码。"""
    try:
        items = kb_share_service.list_share_codes(db, kb_id, current_user.id)
    except ShareError as e:
        raise HTTPException(
            status_code=404, detail={"code": e.code, "message": e.message},
        )
    return {"code": 0, "message": "success", "data": items}


# ── 凭码访问 ──────────────────────────────────────────────

@router.post("/access-by-code")
def access_by_share_code(
    body: AccessByCodeRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """输入分享码，获取知识库信息。全程留痕。"""
    try:
        share, kb = kb_share_service.access_by_share_code(
            db, body.share_code, current_user.id,
        )
    except ShareError as e:
        raise HTTPException(
            status_code=404 if e.code in (40402, 40403) else 403,
            detail={"code": e.code, "message": e.message},
        )

    # 记录访问：谁通过哪个分享码进入了哪个知识库
    kb_share_service.log_access(
        db, kb.id, current_user.id, kb_share_service.ACCESS_VIEW,
        detail=f"通过分享码 {share.share_code} 进入知识库",
        ip_address=request.client.host if request.client else None,
        share_code=share.share_code,
    )
    log_action(
        db, ACTION_KB_SHARE,
        user_id=current_user.id, user_email=current_user.email,
        resource_type="knowledge_base", resource_id=kb.id,
        detail=f"通过分享码 {share.share_code} 访问知识库: {kb.name}",
        ip_address=request.client.host if request.client else None,
    )

    return {
        "code": 0,
        "message": "success",
        "data": {
            "id": kb.id,
            "name": kb.name,
            "description": kb.description,
            "permission": share.permission,
            "shared_by": share.shared_by_id,
            "accessed_at": share.created_at,
        },
    }


# ── 访问日志 ──────────────────────────────────────────────

@router.get("/bases/{kb_id}/access-logs")
def list_access_logs(
    kb_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """查询知识库的访问日志（仅 owner 可查看）。"""
    from llm_agent.models.knowledge_base import KnowledgeBase
    kb = db.query(KnowledgeBase).filter(
        KnowledgeBase.id == kb_id,
        KnowledgeBase.owner_id == current_user.id,
    ).first()
    if not kb:
        raise HTTPException(
            status_code=404,
            detail={"code": 40401, "message": "知识库不存在或无权查看访问日志"},
        )

    items, total = kb_share_service.list_access_logs(
        db, kb_id, page=page, page_size=page_size,
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
