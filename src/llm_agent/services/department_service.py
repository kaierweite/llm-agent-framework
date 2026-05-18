"""
部门管理服务层 —— CRUD、层级查询、成员管理。
"""

from typing import Optional, Tuple, List

from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from llm_agent.models.department import Department
from llm_agent.models.user import User


class DepartmentError(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


# ── 基础 CRUD ──────────────────────────────────────────────────

def create_department(
    db: Session,
    name: str,
    code: str,
    description: str | None = None,
    parent_id: str | None = None,
    leader_id: str | None = None,
    sort_order: int = 0,
) -> Department:
    """创建部门。code 唯一，parent_id 必须指向已存在的部门。"""
    if db.query(Department).filter(Department.code == code).first():
        raise DepartmentError(40901, f"部门编码 '{code}' 已存在")

    if parent_id:
        parent = db.query(Department).filter(Department.id == parent_id).first()
        if not parent:
            raise DepartmentError(40401, "上级部门不存在")
        # 检查循环引用（最多往上查 10 层）
        _check_circular(db, parent_id)

    if leader_id:
        leader = db.query(User).filter(User.id == leader_id).first()
        if not leader:
            raise DepartmentError(40402, "指定负责人不存在")

    dept = Department(
        name=name,
        code=code,
        description=description,
        parent_id=parent_id,
        leader_id=leader_id,
        sort_order=sort_order,
    )
    db.add(dept)
    db.commit()
    db.refresh(dept)
    return dept


def update_department(
    db: Session,
    dept_id: str,
    name: str | None = None,
    description: str | None = None,
    parent_id: str | None = None,
    leader_id: str | None = None,
    sort_order: int | None = None,
    is_active: bool | None = None,
) -> Department:
    """更新部门信息。"""
    dept = db.query(Department).filter(Department.id == dept_id).first()
    if not dept:
        raise DepartmentError(40401, "部门不存在")

    if name is not None:
        dept.name = name
    if description is not None:
        dept.description = description
    if sort_order is not None:
        dept.sort_order = sort_order
    if is_active is not None:
        dept.is_active = is_active

    if parent_id is not None:
        if parent_id == dept_id:
            raise DepartmentError(40001, "不能将部门设为自己的上级")
        if parent_id:
            parent = db.query(Department).filter(Department.id == parent_id).first()
            if not parent:
                raise DepartmentError(40401, "上级部门不存在")
            _check_circular(db, parent_id, exclude_id=dept_id)
        dept.parent_id = parent_id or None

    if leader_id is not None:
        if leader_id:
            leader = db.query(User).filter(User.id == leader_id).first()
            if not leader:
                raise DepartmentError(40402, "指定负责人不存在")
        dept.leader_id = leader_id or None

    db.commit()
    db.refresh(dept)
    return dept


def delete_department(db: Session, dept_id: str) -> None:
    """删除部门（仅当无子部门、无成员时允许）。"""
    dept = db.query(Department).filter(Department.id == dept_id).first()
    if not dept:
        raise DepartmentError(40401, "部门不存在")

    child_count = db.query(Department).filter(Department.parent_id == dept_id).count()
    if child_count > 0:
        raise DepartmentError(40003, f"该部门下有 {child_count} 个子部门，无法删除")

    member_count = db.query(User).filter(User.department_id == dept_id).count()
    if member_count > 0:
        raise DepartmentError(40004, f"该部门下有 {member_count} 名成员，无法删除")

    db.delete(dept)
    db.commit()


def get_department(db: Session, dept_id: str) -> Department:
    """获取单个部门详情。"""
    dept = db.query(Department).filter(Department.id == dept_id).first()
    if not dept:
        raise DepartmentError(40401, "部门不存在")
    return dept


def list_departments(
    db: Session,
    parent_id: str | None = None,
    include_inactive: bool = False,
) -> List[dict]:
    """列出部门树。parent_id=None 时返回顶层部门。"""
    query = db.query(Department)
    if not include_inactive:
        query = query.filter(Department.is_active == True)
    query = query.filter(Department.parent_id == parent_id)
    query = query.order_by(Department.sort_order, Department.name)

    results = []
    for dept in query.all():
        member_count = db.query(User).filter(User.department_id == dept.id).count()
        child_count = db.query(Department).filter(Department.parent_id == dept.id).count()
        results.append({
            "id": dept.id,
            "name": dept.name,
            "code": dept.code,
            "description": dept.description,
            "parent_id": dept.parent_id,
            "leader_id": dept.leader_id,
            "sort_order": dept.sort_order,
            "is_active": dept.is_active,
            "created_at": dept.created_at,
            "updated_at": dept.updated_at,
            "member_count": member_count,
            "child_count": child_count,
        })
    return results


def get_department_tree(
    db: Session,
    include_inactive: bool = False,
) -> List[dict]:
    """递归获取完整部门树。"""
    def _build_tree(parent_id: str | None) -> List[dict]:
        query = db.query(Department)
        if not include_inactive:
            query = query.filter(Department.is_active == True)
        query = query.filter(Department.parent_id == parent_id)
        query = query.order_by(Department.sort_order, Department.name)

        tree = []
        for dept in query.all():
            member_count = db.query(User).filter(User.department_id == dept.id).count()
            node = {
                "id": dept.id,
                "name": dept.name,
                "code": dept.code,
                "description": dept.description,
                "leader_id": dept.leader_id,
                "sort_order": dept.sort_order,
                "is_active": dept.is_active,
                "member_count": member_count,
                "children": _build_tree(dept.id),
            }
            tree.append(node)
        return tree

    return _build_tree(None)


# ── 成员管理 ──────────────────────────────────────────────────

def add_member(db: Session, dept_id: str, user_id: str) -> User:
    """将用户加入部门。"""
    dept = db.query(Department).filter(Department.id == dept_id).first()
    if not dept:
        raise DepartmentError(40401, "部门不存在")
    if not dept.is_active:
        raise DepartmentError(40005, "不能向已停用的部门添加成员")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise DepartmentError(40402, "用户不存在")

    user.department_id = dept_id
    db.commit()
    db.refresh(user)
    return user


def remove_member(db: Session, dept_id: str, user_id: str) -> User:
    """将用户移出部门。"""
    user = db.query(User).filter(User.id == user_id, User.department_id == dept_id).first()
    if not user:
        raise DepartmentError(40402, "该用户不在此部门中")

    user.department_id = None
    db.commit()
    db.refresh(user)
    return user


def batch_add_members(db: Session, dept_id: str, user_ids: List[str]) -> int:
    """批量添加成员，返回实际添加人数。"""
    dept = db.query(Department).filter(Department.id == dept_id).first()
    if not dept:
        raise DepartmentError(40401, "部门不存在")
    if not dept.is_active:
        raise DepartmentError(40005, "不能向已停用的部门添加成员")

    count = 0
    for uid in user_ids:
        user = db.query(User).filter(User.id == uid).first()
        if user:
            user.department_id = dept_id
            count += 1
    db.commit()
    return count


def list_members(
    db: Session,
    dept_id: str,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[User], int]:
    """列出部门成员（分页）。"""
    query = db.query(User).filter(User.department_id == dept_id)
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return items, total


# ── 内部辅助 ──────────────────────────────────────────────────

def _check_circular(db: Session, parent_id: str, exclude_id: str | None = None, depth: int = 0):
    """检查是否会形成循环引用。"""
    if depth > 10:
        raise DepartmentError(40002, "检测到循环引用")

    current = db.query(Department).filter(Department.id == parent_id).first()
    if not current:
        return
    if exclude_id and current.id == exclude_id:
        raise DepartmentError(40002, "检测到循环引用")
    if current.parent_id:
        _check_circular(db, current.parent_id, exclude_id, depth + 1)
