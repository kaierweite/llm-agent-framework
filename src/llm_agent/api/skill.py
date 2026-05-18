from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException

from llm_agent.middleware.auth import get_current_user
from llm_agent.models.user import User
from llm_agent.services import skill_service
from llm_agent.services.skill_service import SkillError


class SkillToggle(BaseModel):
    enabled: bool


router = APIRouter(prefix="/api/skills", tags=["技能管理"])


@router.get("")
def list_skills(current_user: User = Depends(get_current_user)):
    skills = skill_service.list_file_skills()
    return {"code": 0, "message": "success", "data": skills}


@router.put("/{skill_name}/toggle")
def toggle_skill(
    skill_name: str,
    body: SkillToggle,
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail={"code": 40301, "message": "Admin access required"})
    try:
        data = skill_service.toggle_skill_file(skill_name, body.enabled)
    except SkillError as e:
        raise HTTPException(status_code=404 if e.code == 40401 else 400, detail={"code": e.code, "message": e.message})
    return {"code": 0, "message": "success", "data": data}
