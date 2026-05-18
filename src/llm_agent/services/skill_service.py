from typing import Optional, Tuple

import os
import re

from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from llm_agent import PROJECT_ROOT
from llm_agent.models.skill import Skill


class SkillError(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def _skill_to_dict(skill: Skill) -> dict:
    return {
        "id": skill.id,
        "name": skill.name,
        "display_name": skill.display_name,
        "description": skill.description,
        "version": skill.version,
        "author": skill.author,
        "is_enabled": skill.is_enabled,
        "config_schema": skill.config_schema,
        "created_at": skill.created_at,
        "updated_at": skill.updated_at,
    }


def list_skills(
    db: Session, page: int = 1, page_size: int = 20
) -> Tuple[list, int]:
    total = db.query(func.count(Skill.id)).scalar()

    rows = (
        db.query(Skill)
        .order_by(desc(Skill.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = [_skill_to_dict(s) for s in rows]
    return items, total


def get_skill(db: Session, skill_id: str) -> Optional[dict]:
    skill = db.query(Skill).filter(Skill.id == skill_id).first()
    if not skill:
        return None
    return _skill_to_dict(skill)


def create_skill(
    db: Session,
    name: str,
    display_name: str,
    description: str | None = None,
    version: str = "1.0.0",
    author: str | None = None,
    config_schema: str | None = None,
) -> dict:
    existing = db.query(Skill).filter(Skill.name == name).first()
    if existing:
        raise SkillError(40901, f"Skill '{name}' already exists")

    skill = Skill(
        name=name,
        display_name=display_name,
        description=description,
        version=version,
        author=author,
        config_schema=config_schema,
    )
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return _skill_to_dict(skill)


def update_skill(db: Session, skill_id: str, **kwargs) -> Optional[dict]:
    skill = db.query(Skill).filter(Skill.id == skill_id).first()
    if not skill:
        return None

    allowed = {
        "display_name", "description", "version",
        "author", "config_schema", "is_enabled",
    }
    for key, value in kwargs.items():
        if key in allowed:
            setattr(skill, key, value)

    db.commit()
    db.refresh(skill)
    return _skill_to_dict(skill)


def delete_skill(db: Session, skill_id: str) -> bool:
    skill = db.query(Skill).filter(Skill.id == skill_id).first()
    if not skill:
        return False

    db.delete(skill)
    db.commit()
    return True


def toggle_skill_enabled(db: Session, skill_id: str) -> Optional[dict]:
    skill = db.query(Skill).filter(Skill.id == skill_id).first()
    if not skill:
        return None

    skill.is_enabled = not skill.is_enabled
    db.commit()
    db.refresh(skill)
    return _skill_to_dict(skill)


_SKILLS_DIR = os.path.join(PROJECT_ROOT, '.agents', 'skills')


def _parse_yaml_front_matter(content: str) -> dict:
    result = {}
    pattern = r'^---\s*\n(.*?)\n---'
    match = re.search(pattern, content, re.DOTALL)
    if not match:
        return result
    yaml_content = match.group(1)
    name_match = re.search(r'^name:\s*(.+)$', yaml_content, re.MULTILINE)
    if name_match:
        result['name'] = name_match.group(1).strip().strip('"').strip("'")
    desc_match = re.search(r'^description:\s*(.+)$', yaml_content, re.MULTILINE)
    if desc_match:
        result['description'] = desc_match.group(1).strip().strip('"').strip("'")
    return result


def list_file_skills() -> list[dict]:
    if not os.path.isdir(_SKILLS_DIR):
        return []

    skills = []
    for name in sorted(os.listdir(_SKILLS_DIR)):
        skill_dir = os.path.join(_SKILLS_DIR, name)
        if not os.path.isdir(skill_dir):
            continue

        skill_md = os.path.join(skill_dir, 'SKILL.md')
        description = ""
        display_name = name
        if os.path.isfile(skill_md):
            try:
                with open(skill_md, 'r', encoding='utf-8') as f:
                    content = f.read()
                fm = _parse_yaml_front_matter(content)
                if fm.get('name'):
                    display_name = fm['name']
                description = fm.get('description', '')
            except Exception:
                pass

        enabled = not os.path.isfile(os.path.join(skill_dir, '.disabled'))
        skills.append({
            "name": name,
            "display_name": display_name,
            "description": description,
            "enabled": enabled,
        })

    return skills


def toggle_skill_file(skill_name: str, enabled: bool) -> dict:
    if '..' in skill_name or '/' in skill_name or '\\' in skill_name or os.path.isabs(skill_name):
        raise SkillError(40001, f"Invalid skill name: '{skill_name}'")

    skill_dir = os.path.normpath(os.path.join(_SKILLS_DIR, skill_name))
    if not skill_dir.startswith(os.path.normpath(_SKILLS_DIR)):
        raise SkillError(40001, f"Invalid skill name: '{skill_name}'")

    if not os.path.isdir(skill_dir):
        raise SkillError(40401, f"Skill '{skill_name}' not found")

    marker = os.path.join(skill_dir, '.disabled')
    if enabled:
        if os.path.isfile(marker):
            os.remove(marker)
    else:
        if not os.path.isfile(marker):
            with open(marker, 'w') as f:
                f.write('')

    skills = list_file_skills()
    for s in skills:
        if s['name'] == skill_name:
            return s

    return {"name": skill_name, "enabled": enabled}
