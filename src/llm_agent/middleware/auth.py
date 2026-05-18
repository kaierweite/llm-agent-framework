from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from llm_agent.database import get_db
from llm_agent.models.user import User
from llm_agent.services.auth_service import decode_token, AuthError

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(status_code=401, detail={"code": 40101, "message": "Missing authorization token"})

    try:
        payload = decode_token(credentials.credentials)
    except AuthError as e:
        raise HTTPException(status_code=401, detail={"code": e.code, "message": e.message})

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail={"code": 40101, "message": "Invalid token payload"})

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail={"code": 40101, "message": "User not found"})
    if not user.is_active:
        raise HTTPException(status_code=401, detail={"code": 40101, "message": "Account disabled"})

    return user


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """FastAPI 依赖项：要求当前用户为管理员。"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail={"code": 40301, "message": "Admin access required"})
    return current_user


async def require_admin_or_auditor(current_user: User = Depends(get_current_user)) -> User:
    """FastAPI 依赖项：要求当前用户为管理员或审计员。"""
    if current_user.role not in ("admin", "auditor"):
        raise HTTPException(status_code=403, detail={"code": 40301, "message": "Admin or auditor access required"})
    return current_user
