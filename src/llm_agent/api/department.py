"""
部门管理 API —— CRUD、层级树、成员管理。

权限：
- 管理员：全部操作
- 部门负责人：管理部门成员（添加/移除/查看）
- 普通成员：查看部门信息
"""

from typing import Optional, List
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from llm_agent.database import get_db
from llm_agent.middleware.auth import get_current_user, require_admin
from llm_agent.models.user import User
from llm_agent.services import department_service
from llm_agent.services.department_service import DepartmentError
from llm_agent.services.audit_service import log_action

router = APIRouter(prefix="/api/departments", tags=["部门管理"])


# ── 审计日志动作常量 ──────────────────────────────────────────

ACTION_DEPT_CREATE = "admin.department_create"
ACTION_DEPT_UPDATE = "admin.department_update"
ACTION_DEPT_DELETE = "admin.department_delete"
ACTION_DEPT_MEMBER_ADD = "admin.department_member_add"
ACTION_DEPT_MEMBER_REMOVE = "admin.department_member_remove"
ACTION_DEPT_MEMBER_BATCH_ADD = "admin.department_member_batch_add"


# ── 请求/响应模型 ─────────────────────────────────────────────

class DepartmentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    description: Optional[str] = Field(None, max_length=500)
    parent_id: Optional[str] = None
    leader_id: Optional[str] = None
    sort_order: int = 0


class DepartmentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    parent_id: Optional[str] = None
    leader_id: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class MemberAdd(BaseModel):
    user_id: str


class BatchMemberAdd(BaseModel):
    user_ids: List[str]


# ── 辅助函数 ──────────────────────────────────────────────────

def _dept_response(dept) -> dict:
    return {
        "id": dept.id,
        "name": dept.name,
        "code": dept.code,
        "description": dept.description,
        "parent_id": dept.parent_id,
        "leader_id": dept.leader_id,
        "sort_order": dept.sort_order,
        "is_active": dept.is_active,
        "created_at": dept.created_at.isoformat() if dept.created_at else None,
        "updated_at": dept.updated_at.isoformat() if dept.updated_at else None,
    }


def _user_brief(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "role": user.role,
        "avatar_url": user.avatar_url,
        "department_id": user.department_id,
        "is_active": user.is_active,
    }


def _handle_error(e: DepartmentError):
    status_map = {
        40901: 409,
        40401: 404,
        40402: 404,
        40001: 400,
        40002: 400,
        40003: 400,
        40004: 400,
        40005: 400,
    }
    raise HTTPException(
        status_code=status_map.get(e.code, 400),
        detail={"code": e.code, "message": e.message},
    )


# ── 部门 CRUD（仅管理员） ────────────────────────────────────

@router.post("", status_code=201)
def create_department(
    body: DepartmentCreate,
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """创建部门（仅管理员）。"""
    try:
        dept = department_service.create_department(
            db,
            name=body.name,
            code=body.code,
            description=body.description,
            parent_id=body.parent_id,
            leader_id=body.leader_id,
            sort_order=body.sort_order,
        )
    except DepartmentError as e:
        _handle_error(e)

    log_action(
        db, ACTION_DEPT_CREATE,
        user_id=current_user.id, user_email=current_user.email,
        resource_type="department", resource_id=dept.id,
        detail=f"创建部门: {dept.name} ({dept.code})",
        ip_address=request.client.host if request.client else None,
    )
    return {"code": 0, "message": "success", "data": _dept_response(dept)}


@router.get("")
def list_departments(
    parent_id: Optional[str] = Query(None, description="上级部门ID，为空则返回顶层"),
    include_inactive: bool = Query(False, description="是否包含已停用部门"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """列出部门（支持按上级筛选）。"""
    items = department_service.list_departments(
        db, parent_id=parent_id, include_inactive=include_inactive,
    )
    return {"code": 0, "message": "success", "data": items}


@router.get("/tree")
def get_department_tree(
    include_inactive: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取完整部门树。"""
    tree = department_service.get_department_tree(db, include_inactive=include_inactive)
    return {"code": 0, "message": "success", "data": tree}


@router.get("/{dept_id}")
def get_department(
    dept_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取单个部门详情。"""
    try:
        dept = department_service.get_department(db, dept_id)
    except DepartmentError as e:
        _handle_error(e)

    member_count = db.query(User).filter(User.department_id == dept_id).count()
    data = _dept_response(dept)
    data["member_count"] = member_count
    return {"code": 0, "message": "success", "data": data}


@router.put("/{dept_id}")
def update_department(
    dept_id: str,
    body: DepartmentUpdate,
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """更新部门信息（仅管理员）。"""
    try:
        dept = department_service.update_department(
            db, dept_id,
            name=body.name,
            description=body.description,
            parent_id=body.parent_id,
            leader_id=body.leader_id,
            sort_order=body.sort_order,
            is_active=body.is_active,
        )
    except DepartmentError as e:
        _handle_error(e)

    log_action(
        db, ACTION_DEPT_UPDATE,
        user_id=current_user.id, user_email=current_user.email,
        resource_type="department", resource_id=dept_id,
        detail=f"更新部门: {dept.name}",
        ip_address=request.client.host if request.client else None,
    )
    return {"code": 0, "message": "success", "data": _dept_response(dept)}


@router.delete("/{dept_id}")
def delete_department(
    dept_id: str,
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """删除部门（仅管理员，需无子部门和成员）。"""
    try:
        dept = department_service.get_department(db, dept_id)
        dept_name = dept.name
        department_service.delete_department(db, dept_id)
    except DepartmentError as e:
        _handle_error(e)

    log_action(
        db, ACTION_DEPT_DELETE,
        user_id=current_user.id, user_email=current_user.email,
        resource_type="department", resource_id=dept_id,
        detail=f"删除部门: {dept_name}",
        ip_address=request.client.host if request.client else None,
    )
    return {"code": 0, "message": "success", "data": None}


# ── 成员管理 ──────────────────────────────────────────────────

@router.get("/{dept_id}/members")
def list_members(
    dept_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """列出部门成员。"""
    try:
        department_service.get_department(db, dept_id)  # 验证部门存在
    except DepartmentError as e:
        _handle_error(e)

    items, total = department_service.list_members(db, dept_id, page=page, page_size=page_size)
    return {
        "code": 0,
        "message": "success",
        "data": {
            "items": [_user_brief(u) for u in items],
            "total": total,
            "page": page,
            "page_size": page_size,
        },
    }


@router.post("/{dept_id}/members")
def add_member(
    dept_id: str,
    body: MemberAdd,
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """添加成员到部门（仅管理员）。"""
    try:
        user = department_service.add_member(db, dept_id, body.user_id)
    except DepartmentError as e:
        _handle_error(e)

    log_action(
        db, ACTION_DEPT_MEMBER_ADD,
        user_id=current_user.id, user_email=current_user.email,
        resource_type="department", resource_id=dept_id,
        detail=f"添加成员 {user.email} 到部门",
        ip_address=request.client.host if request.client else None,
    )
    return {"code": 0, "message": "success", "data": _user_brief(user)}


@router.post("/{dept_id}/members/batch")
def batch_add_members(
    dept_id: str,
    body: BatchMemberAdd,
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """批量添加成员到部门（仅管理员）。"""
    try:
        count = department_service.batch_add_members(db, dept_id, body.user_ids)
    except DepartmentError as e:
        _handle_error(e)

    log_action(
        db, ACTION_DEPT_MEMBER_BATCH_ADD,
        user_id=current_user.id, user_email=current_user.email,
        resource_type="department", resource_id=dept_id,
        detail=f"批量添加 {count} 名成员到部门",
        ip_address=request.client.host if request.client else None,
    )
    return {"code": 0, "message": "success", "data": {"added": count}}


@router.delete("/{dept_id}/members/{user_id}")
def remove_member(
    dept_id: str,
    user_id: str,
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """从部门移除成员（仅管理员）。"""
    try:
        user = department_service.remove_member(db, dept_id, user_id)
    except DepartmentError as e:
        _handle_error(e)

    log_action(
        db, ACTION_DEPT_MEMBER_REMOVE,
        user_id=current_user.id, user_email=current_user.email,
        resource_type="department", resource_id=dept_id,
        detail=f"从部门移除成员 {user.email}",
        ip_address=request.client.host if request.client else None,
    )
    return {"code": 0, "message": "success", "data": _user_brief(user)}


# ── 未分类成员查询 ────────────────────────────────────────────

@router.get("/unassigned/users")
def list_unassigned_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """列出未分配部门的用户（仅管理员）。"""
    query = db.query(User).filter(User.department_id == None)
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "code": 0,
        "message": "success",
        "data": {
            "items": [_user_brief(u) for u in items],
            "total": total,
            "page": page,
            "page_size": page_size,
        },
    }
