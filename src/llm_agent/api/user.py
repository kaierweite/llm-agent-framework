from typing import Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from llm_agent.database import get_db
from llm_agent.middleware.auth import get_current_user
from llm_agent.models.user import User
from llm_agent.services.auth_service import hash_password, check_password


class UserProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None


class UserPasswordChange(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8)


router = APIRouter(prefix="/api/user", tags=["用户"])


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.refresh(current_user, ["department"])
    department_name = current_user.department.name if current_user.department else None
    return {
        "code": 0,
        "message": "success",
        "data": {
            "id": current_user.id,
            "email": current_user.email,
            "display_name": current_user.display_name,
            "role": current_user.role,
            "avatar_url": current_user.avatar_url,
            "department_id": current_user.department_id,
            "department_name": department_name,
            "created_at": current_user.created_at,
        },
    }


@router.put("/me")
def update_me(
    body: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.display_name is not None:
        current_user.display_name = body.display_name
    if body.avatar_url is not None:
        current_user.avatar_url = body.avatar_url

    db.commit()
    db.refresh(current_user, ["department"])
    department_name = current_user.department.name if current_user.department else None
    return {
        "code": 0,
        "message": "success",
        "data": {
            "id": current_user.id,
            "email": current_user.email,
            "display_name": current_user.display_name,
            "role": current_user.role,
            "avatar_url": current_user.avatar_url,
            "department_id": current_user.department_id,
            "department_name": department_name,
            "created_at": current_user.created_at,
        },
    }


@router.post("/me/change-password")
def change_password(
    body: UserPasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not check_password(body.old_password, current_user.password_hash):
        raise HTTPException(
            status_code=400,
            detail={"code": 40001, "message": "Invalid old password"},
        )

    current_user.password_hash = hash_password(body.new_password)
    db.commit()
    db.refresh(current_user)
    return {"code": 0, "message": "Password updated successfully", "data": None}
