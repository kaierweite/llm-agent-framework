import os

from fastapi import APIRouter, Depends, HTTPException, Query, File, UploadFile, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from llm_agent.database import get_db
from llm_agent.middleware.auth import get_current_user
from llm_agent.models.user import User
from llm_agent.api.schemas.knowledge import (
    KnowledgeBaseCreate,
    KnowledgeBaseRename,
    KnowledgeBaseQuery,
)
from llm_agent.services import knowledge_service
from llm_agent.services.knowledge_service import KnowledgeError
from llm_agent.services.kb_share_service import (
    can_access, get_accessible_knowledge_base, log_access,
    ACCESS_VIEW, ACCESS_QUERY, ACCESS_DOWNLOAD,
)
from llm_agent.services.audit_service import (
    log_action,
    ACTION_KB_CREATE, ACTION_KB_DELETE, ACTION_KB_UPDATE,
    ACTION_DOC_UPLOAD, ACTION_DOC_DELETE,
)

router = APIRouter(prefix="/api/knowledge", tags=["知识库"])


@router.get("/users")
def list_all_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """列出所有用户（供知识库成员管理使用，无需 admin 权限）。"""
    from llm_agent.services import admin_service
    items, total = admin_service.list_users(db, page=1, page_size=1000)
    return {
        "code": 0,
        "message": "success",
        "data": {"items": items, "total": total},
    }


@router.post("/bases", status_code=201)
def create_knowledge_base(
    body: KnowledgeBaseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        kb = knowledge_service.create_knowledge_base(
            db, current_user.id, body.name, body.description or "",
            chat_provider=body.chat_provider,
            chat_model=body.chat_model,
        )
    except KnowledgeError as e:
        # 409 冲突（如名称重复）直接返回对应状态码，其他错误返回 502
        status = e.code if 400 <= e.code < 600 else 502
        raise HTTPException(
            status_code=status, detail={"code": e.code, "message": e.message}
        )
    log_action(db, ACTION_KB_CREATE, user_id=current_user.id, user_email=current_user.email,
               resource_type="knowledge_base", resource_id=kb.id,
               detail=f"创建知识库: {body.name}")
    return {
        "code": 0,
        "message": "success",
        "data": {
            "id": kb.id,
            "name": kb.name,
            "description": kb.description,
            "anythingllm_workspace_slug": kb.anythingllm_workspace_slug,
            "is_active": kb.is_active,
            "created_at": kb.created_at,
            "updated_at": kb.updated_at,
        },
    }


@router.get("/bases")
def list_knowledge_bases(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items, total = knowledge_service.list_knowledge_bases(
        db, current_user.id, page=page, page_size=page_size
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


@router.get("/bases/{kb_id}")
def get_knowledge_base_detail(
    kb_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 先检查 owner，再检查分享权限
    kb = knowledge_service.get_knowledge_base(db, current_user.id, kb_id)
    is_owner = kb is not None
    permission = "owner" if is_owner else None
    if not is_owner:
        share = can_access(db, kb_id, current_user.id)
        if not share:
            raise HTTPException(
                status_code=404,
                detail={"code": 40401, "message": "Knowledge base not found"},
            )
        kb = get_accessible_knowledge_base(db, kb_id, current_user.id)
        permission = share.permission  # read / write / admin

    # 记录访问
    log_access(db, kb_id, current_user.id, ACCESS_VIEW,
               detail="查看知识库详情",
               ip_address=request.client.host if request.client else None)

    docs_items, _ = knowledge_service.list_documents(
        db, kb.owner_id, kb_id, page=1, page_size=10000
    )

    return {
        "code": 0,
        "message": "success",
        "data": {
            "id": kb.id,
            "name": kb.name,
            "description": kb.description,
            "document_count": len(docs_items),
            "is_active": kb.is_active,
            "is_owner": is_owner,
            "permission": permission,
            "created_at": kb.created_at,
            "updated_at": kb.updated_at,
            "documents": docs_items,
        },
    }


@router.put("/bases/{kb_id}")
def rename_knowledge_base(
    kb_id: str,
    body: KnowledgeBaseRename,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 权限校验：owner 直接通过，否则需要 write 或 admin 权限
    kb = knowledge_service.get_knowledge_base(db, current_user.id, kb_id)
    if not kb:
        share = can_access(db, kb_id, current_user.id)
        if not share:
            raise HTTPException(
                status_code=404,
                detail={"code": 40401, "message": "Knowledge base not found"},
            )
        if share.permission not in ("write", "admin"):
            raise HTTPException(
                status_code=403,
                detail={"code": 40301, "message": "无权修改知识库，需要 write 或 admin 权限"},
            )
        kb = get_accessible_knowledge_base(db, kb_id, current_user.id)

    try:
        kb = knowledge_service.rename_knowledge_base(
            db, kb.owner_id, kb_id, body.name, body.description
        )
    except KnowledgeError as e:
        raise HTTPException(
            status_code=404, detail={"code": e.code, "message": e.message}
        )
    log_action(db, ACTION_KB_UPDATE, user_id=current_user.id, user_email=current_user.email,
               resource_type="knowledge_base", resource_id=kb_id,
               detail=f"重命名知识库: {body.name}")
    return {
        "code": 0,
        "message": "success",
        "data": {
            "id": kb.id,
            "name": kb.name,
            "description": kb.description,
            "is_active": kb.is_active,
            "created_at": kb.created_at,
            "updated_at": kb.updated_at,
        },
    }


@router.delete("/bases/{kb_id}")
def delete_knowledge_base(
    kb_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 权限校验：只有 owner 或 admin 权限才能删除知识库
    kb = knowledge_service.get_knowledge_base(db, current_user.id, kb_id)
    if not kb:
        share = can_access(db, kb_id, current_user.id)
        if not share:
            raise HTTPException(
                status_code=404,
                detail={"code": 40401, "message": "Knowledge base not found"},
            )
        if share.permission != "admin":
            raise HTTPException(
                status_code=403,
                detail={"code": 40301, "message": "无权删除知识库，需要 admin 权限"},
            )
        kb = get_accessible_knowledge_base(db, kb_id, current_user.id)

    deleted = knowledge_service.delete_knowledge_base(db, kb.owner_id, kb_id)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail={"code": 40401, "message": "Knowledge base not found"},
        )
    log_action(db, ACTION_KB_DELETE, user_id=current_user.id, user_email=current_user.email,
               resource_type="knowledge_base", resource_id=kb_id, detail="删除知识库")
    return {"code": 0, "message": "Knowledge base deleted", "data": None}


@router.post("/bases/{kb_id}/documents", status_code=201)
async def upload_document(
    kb_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 权限校验：owner 直接通过，否则需要 write 或 admin 权限
    kb = knowledge_service.get_knowledge_base(db, current_user.id, kb_id)
    if not kb:
        share = can_access(db, kb_id, current_user.id)
        if not share:
            raise HTTPException(
                status_code=404,
                detail={"code": 40401, "message": "Knowledge base not found"},
            )
        if share.permission not in ("write", "admin"):
            raise HTTPException(
                status_code=403,
                detail={"code": 40301, "message": "无权上传文档，需要 write 或 admin 权限"},
            )
        kb = get_accessible_knowledge_base(db, kb_id, current_user.id)

    try:
        doc = knowledge_service.upload_document(db, kb.owner_id, kb_id, file)
    except KnowledgeError as e:
        status = 404 if e.code == 40401 else 413 if e.code == 41301 else 400
        raise HTTPException(
            status_code=status, detail={"code": e.code, "message": e.message}
        )
    log_action(db, ACTION_DOC_UPLOAD, user_id=current_user.id, user_email=current_user.email,
               resource_type="document", resource_id=doc.id,
               detail=f"上传文档: {doc.filename} ({doc.file_type})")
    return {
        "code": 0,
        "message": "success",
        "data": {
            "id": doc.id,
            "filename": doc.filename,
            "file_size": doc.file_size,
            "file_type": doc.file_type,
            "upload_status": doc.upload_status,
            "error_message": doc.error_message,
            "created_at": doc.created_at,
        },
    }


@router.get("/bases/{kb_id}/documents")
def list_documents(
    kb_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 检查 owner 或分享权限
    kb = knowledge_service.get_knowledge_base(db, current_user.id, kb_id)
    if not kb:
        share = can_access(db, kb_id, current_user.id)
        if not share:
            raise HTTPException(
                status_code=404, detail={"code": 40401, "message": "Knowledge base not found"},
            )
        kb = get_accessible_knowledge_base(db, kb_id, current_user.id)

    try:
        items, total = knowledge_service.list_documents(
            db, kb.owner_id, kb_id, page=page, page_size=page_size
        )
    except KnowledgeError as e:
        raise HTTPException(
            status_code=404, detail={"code": e.code, "message": e.message}
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


@router.delete("/documents/{doc_id}")
def delete_document(
    doc_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 先查文档所属知识库
    from llm_agent.models.document import Document
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(
            status_code=404,
            detail={"code": 40401, "message": "Document not found"},
        )

    # 权限校验：owner 直接通过，否则需要 write 或 admin 权限
    kb = knowledge_service.get_knowledge_base(db, current_user.id, doc.knowledge_base_id)
    if not kb:
        share = can_access(db, doc.knowledge_base_id, current_user.id)
        if not share:
            raise HTTPException(
                status_code=404,
                detail={"code": 40401, "message": "Document not found"},
            )
        if share.permission not in ("write", "admin"):
            raise HTTPException(
                status_code=403,
                detail={"code": 40301, "message": "无权删除文档，需要 write 或 admin 权限"},
            )
        kb = get_accessible_knowledge_base(db, doc.knowledge_base_id, current_user.id)

    deleted = knowledge_service.delete_document(db, kb.owner_id, doc_id)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail={"code": 40401, "message": "Document not found"},
        )
    log_action(db, ACTION_DOC_DELETE, user_id=current_user.id, user_email=current_user.email,
               resource_type="document", resource_id=doc_id, detail="删除文档")
    return {"code": 0, "message": "Document deleted", "data": None}


@router.post("/bases/{kb_id}/query")
def query_knowledge_base(
    kb_id: str,
    body: KnowledgeBaseQuery,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 检查 owner 或分享权限（query 权限）
    kb = knowledge_service.get_knowledge_base(db, current_user.id, kb_id)
    if not kb:
        share = can_access(db, kb_id, current_user.id)
        if not share:
            raise HTTPException(
                status_code=404, detail={"code": 40401, "message": "Knowledge base not found"},
            )
        kb = get_accessible_knowledge_base(db, kb_id, current_user.id)

    # 记录查询访问
    log_access(db, kb_id, current_user.id, ACCESS_QUERY,
               detail=f"查询: {body.question[:200]}",
               ip_address=request.client.host if request.client else None)

    try:
        answer = knowledge_service.query_knowledge_base(
            db, kb.owner_id, kb_id, body.question
        )
    except KnowledgeError as e:
        raise HTTPException(
            status_code=404 if e.code == 40401 else 502,
            detail={"code": e.code, "message": e.message},
        )
    return {
        "code": 0,
        "message": "success",
        "data": {"answer": answer},
    }


@router.get("/documents/{doc_id}/preview")
def preview_document(
    doc_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from llm_agent.models.document import Document
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(
            status_code=404, detail={"code": 40401, "message": "Document not found"},
        )

    # 检查 owner 或分享权限
    kb = knowledge_service.get_knowledge_base(db, current_user.id, doc.knowledge_base_id)
    if not kb:
        share = can_access(db, doc.knowledge_base_id, current_user.id)
        if not share:
            raise HTTPException(
                status_code=404, detail={"code": 40401, "message": "Document not found"},
            )
        kb = get_accessible_knowledge_base(db, doc.knowledge_base_id, current_user.id)

    # 记录访问
    log_access(db, doc.knowledge_base_id, current_user.id, ACCESS_VIEW,
               detail=f"预览文档: {doc.filename}",
               ip_address=request.client.host if request.client else None)

    result = knowledge_service.preview_document(db, kb.owner_id, doc_id)
    if not result:
        raise HTTPException(
            status_code=404, detail={"code": 40401, "message": "Document not found"},
        )
    return {"code": 0, "message": "success", "data": result}


@router.get("/documents/{doc_id}/raw")
def download_document(
    doc_id: str,
    request: Request,
    token: str = Query(None),
    db: Session = Depends(get_db),
):
    """下载/预览原始文件。支持 ?token=xxx 查询参数（用于 iframe 嵌入 PDF）。"""
    from llm_agent.models.document import Document
    from llm_agent.services.auth_service import decode_token, AuthError
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

    # 手动认证：先尝试 Authorization header，再尝试 query token
    user = None

    # 1. 尝试 Authorization header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        try:
            payload = decode_token(auth_header[7:])
            uid = payload.get("sub")
            if uid:
                user = db.query(User).filter(User.id == uid, User.is_active == True).first()
        except AuthError:
            pass

    # 2. 尝试 query token（iframe 场景）
    if not user and token:
        try:
            payload = decode_token(token)
            uid = payload.get("sub")
            if uid:
                user = db.query(User).filter(User.id == uid, User.is_active == True).first()
        except AuthError:
            pass

    if not user:
        raise HTTPException(status_code=401, detail={"code": 40101, "message": "Missing or invalid token"})

    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(
            status_code=404, detail={"code": 40401, "message": "Document not found"},
        )

    # 检查 owner 或分享权限
    kb = knowledge_service.get_knowledge_base(db, user.id, doc.knowledge_base_id)
    if not kb:
        share = can_access(db, doc.knowledge_base_id, user.id)
        if not share:
            raise HTTPException(
                status_code=404, detail={"code": 40401, "message": "Document not found"},
            )
        kb = get_accessible_knowledge_base(db, doc.knowledge_base_id, user.id)

    # 记录下载
    log_access(db, doc.knowledge_base_id, user.id, ACCESS_DOWNLOAD,
               detail=f"下载文档: {doc.filename}",
               ip_address=request.client.host if request.client else None)

    if not doc.file_path or not os.path.exists(doc.file_path):
        raise HTTPException(
            status_code=404, detail={"code": 40401, "message": "Document file not found"},
        )

    media_types = {
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "doc": "application/msword",
        "txt": "text/plain",
        "md": "text/markdown",
    }
    media_type = media_types.get((doc.file_type or "").lower(), "application/octet-stream")

    from starlette.responses import Response
    from urllib.parse import quote
    response = FileResponse(
        path=doc.file_path,
        media_type=media_type,
    )
    # 强制 inline 预览，不触发浏览器下载
    # RFC 5987 编码：filename* 支持 UTF-8 中文文件名
    encoded_name = quote(doc.filename)
    response.headers["Content-Disposition"] = f"inline; filename*=UTF-8''{encoded_name}"
    return response


# ==================== 知识库成员管理 ====================

@router.get("/bases/{kb_id}/members")
def list_knowledge_base_members(
    kb_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """列出知识库的所有成员。"""
    members = knowledge_service.list_members(db, kb_id, current_user.id)
    return {
        "code": 0,
        "message": "success",
        "data": members,
    }


@router.post("/bases/{kb_id}/members")
def add_knowledge_base_member(
    kb_id: str,
    body: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """添加知识库成员。
    
    支持两种方式：
    1. 通过 user_id 添加：{ "user_id": "xxx" }
    2. 通过 email 添加：{ "email": "xxx@example.com" }
    
    可选参数：permission (read/write/admin)
    """
    user_id = body.get("user_id")
    email = body.get("email")
    permission = body.get("permission", "read")
    
    try:
        member = knowledge_service.add_member(db, kb_id, current_user.id, user_id, email, permission)
    except KnowledgeError as e:
        raise HTTPException(
            status_code=400, detail={"code": e.code, "message": e.message}
        )
    
    return {
        "code": 0,
        "message": "success",
        "data": member,
    }


@router.delete("/bases/{kb_id}/members/{user_id}")
def remove_knowledge_base_member(
    kb_id: str,
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """移除知识库成员。"""
    try:
        knowledge_service.remove_member(db, kb_id, current_user.id, user_id)
    except KnowledgeError as e:
        raise HTTPException(
            status_code=404, detail={"code": e.code, "message": e.message}
        )
    
    return {
        "code": 0,
        "message": "success",
        "data": None,
    }


@router.put("/bases/{kb_id}/members/{user_id}")
def update_knowledge_base_member_permission(
    kb_id: str,
    user_id: str,
    body: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新知识库成员权限。"""
    permission = body.get("permission")
    if not permission:
        raise HTTPException(
            status_code=400, detail={"code": 40001, "message": "permission is required"}
        )
    
    try:
        member = knowledge_service.update_member_permission(db, kb_id, current_user.id, user_id, permission)
    except KnowledgeError as e:
        raise HTTPException(
            status_code=404, detail={"code": e.code, "message": e.message}
        )
    
    return {
        "code": 0,
        "message": "success",
        "data": member,
    }
