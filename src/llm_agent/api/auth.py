from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from llm_agent.database import get_db
from llm_agent.middleware.auth import get_current_user
from llm_agent.models.user import User
from llm_agent.api.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    PasswordChangeRequest,
    UserResponse,
    AuthData,
)
from llm_agent.services.auth_service import register, login, change_password, AuthError
from llm_agent.services.audit_service import log_action, ACTION_USER_LOGIN, ACTION_USER_REGISTER, ACTION_USER_PASSWORD_CHANGE, ACTION_USER_LOGOUT

router = APIRouter(prefix="/api/auth", tags=["认证"])


def _user_response(user: User, db: Session = None) -> UserResponse:
    department_name = None
    if db and user.department_id:
        db.refresh(user, ["department"])
        if user.department:
            department_name = user.department.name
    return UserResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=user.role,
        avatar_url=user.avatar_url,
        department_id=user.department_id,
        department_name=department_name,
        created_at=user.created_at,
    )


@router.post("/register", status_code=201)
def register_endpoint(body: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    try:
        user, token = register(db, body.email, body.password, body.display_name)
    except AuthError as e:
        raise HTTPException(status_code=409 if e.code == 40901 else 400, detail={"code": e.code, "message": e.message})
    log_action(db, ACTION_USER_REGISTER, user_id=user.id, user_email=user.email,
               resource_type="user", resource_id=user.id, detail=f"注册成功：{body.email}",
               ip_address=request.client.host if request.client else None)
    return {
        "code": 0,
        "message": "success",
        "data": AuthData(user=_user_response(user, db), access_token=token).model_dump(mode="json"),
    }


@router.post("/login")
def login_endpoint(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    try:
        user, token = login(db, body.email, body.password)
    except AuthError as e:
        log_action(db, ACTION_USER_LOGIN, user_email=body.email, detail=f"登录失败: {e.message}",
                   ip_address=request.client.host if request.client else None)
        raise HTTPException(status_code=401, detail={"code": e.code, "message": e.message})
    log_action(db, ACTION_USER_LOGIN, user_id=user.id, user_email=user.email,
               detail="登录成功", ip_address=request.client.host if request.client else None)
    return {
        "code": 0,
        "message": "success",
        "data": AuthData(user=_user_response(user, db), access_token=token).model_dump(mode="json"),
    }


@router.get("/me")
def me_endpoint(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {
        "code": 0,
        "message": "success",
        "data": _user_response(current_user, db).model_dump(mode="json"),
    }


@router.put("/password")
def password_endpoint(
    body: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        change_password(db, current_user.id, body.old_password, body.new_password)
    except AuthError as e:
        raise HTTPException(status_code=401, detail={"code": e.code, "message": e.message})
    log_action(db, ACTION_USER_PASSWORD_CHANGE, user_id=current_user.id, user_email=current_user.email,
               resource_type="user", resource_id=current_user.id, detail="修改密码成功")
    return {"code": 0, "message": "Password updated successfully", "data": None}

@router.post("/logout")
def logout_endpoint(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    log_action(db, ACTION_USER_LOGOUT, user_id=current_user.id, user_email=current_user.email,
               resource_type="user", resource_id=current_user.id, detail="用户登出",
               ip_address=request.client.host if request.client else None)
    return {"code": 0, "message": "success", "data": None}
