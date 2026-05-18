import os
import re
import json

from llm_agent import PROJECT_ROOT

SKILL_TOOL_DEFINITIONS = {
    "list_available_skills": {
        "type": "function",
        "function": {
            "name": "list_available_skills",
            "description": "读取技能列表，列出所有可用的技能及其描述信息",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    "load_skill_content": {
        "type": "function",
        "function": {
            "name": "load_skill_content",
            "description": "加载指定技能的内容，当需要使用某个技能时调用此函数获取技能详情",
            "parameters": {
                "type": "object",
                "properties": {
                    "skill_name": {
                        "type": "string",
                        "description": "要加载的技能名称"
                    }
                },
                "required": ["skill_name"]
            }
        }
    },
}

def _parse_yaml_front_matter(content: str) -> dict:
    front_matter = {}
    pattern = r'^---\s*\n(.*?)\n---'
    match = re.search(pattern, content, re.DOTALL)
    
    if not match:
        return front_matter
    
    yaml_content = match.group(1)
    
    name_match = re.search(r'^name:\s*(.+)$', yaml_content, re.MULTILINE)
    if name_match:
        front_matter['name'] = name_match.group(1).strip().strip('"').strip("'")
    
    desc_match = re.search(r'^description:\s*(.+)$', yaml_content, re.MULTILINE)
    if desc_match:
        desc_value = desc_match.group(1).strip().strip('"').strip("'")
        front_matter['description'] = desc_value
    
    return front_matter


def list_available_skills() -> str:
    skills_dir = os.path.join(PROJECT_ROOT, '.agents', 'skills')
    
    if not os.path.isdir(skills_dir):
        return json.dumps({"skills": [], "error": f"Skills directory not found at '{skills_dir}'"}, ensure_ascii=False)
    
    try:
        subdirs = [d for d in os.listdir(skills_dir) 
                   if os.path.isdir(os.path.join(skills_dir, d))]
        
        if not subdirs:
            return json.dumps({"skills": []}, ensure_ascii=False)
        
        skills = []
        
        for subdir in subdirs:
            skill_md_path = os.path.join(skills_dir, subdir, 'SKILL.md')
            
            if not os.path.isfile(skill_md_path):
                continue
            
            try:
                with open(skill_md_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                front_matter = _parse_yaml_front_matter(content)
                
                skill_info = {
                    'name': front_matter.get('name', subdir),
                    'description': front_matter.get('description', 'No description available')
                }
                skills.append(skill_info)
                
            except Exception as e:
                continue
        
        if not skills:
            return json.dumps({"skills": []}, ensure_ascii=False)
        
        return json.dumps({"skills": skills}, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({"skills": [], "error": f"Error listing skills: {str(e)}"}, ensure_ascii=False)


def load_skill_content(skill_name: str) -> str:
    skills_dir = os.path.join(PROJECT_ROOT, '.agents', 'skills')
    
    if not os.path.isdir(skills_dir):
        return json.dumps({"error": f"Skills directory not found at '{skills_dir}'"}, ensure_ascii=False)
    
    if '..' in skill_name or '/' in skill_name or '\\' in skill_name or os.path.isabs(skill_name):
        return json.dumps({"error": f"Invalid skill name: '{skill_name}'"}, ensure_ascii=False)
    
    skill_dir = os.path.join(skills_dir, skill_name)
    skill_dir = os.path.normpath(skill_dir)
    if not skill_dir.startswith(os.path.normpath(skills_dir)):
        return json.dumps({"error": f"Invalid skill name: '{skill_name}'"}, ensure_ascii=False)
    
    if not os.path.isdir(skill_dir):
        return json.dumps({"error": f"Skill '{skill_name}' not found"}, ensure_ascii=False)
    
    skill_md_path = os.path.join(skill_dir, 'SKILL.md')
    
    if not os.path.isfile(skill_md_path):
        return json.dumps({"error": f"SKILL.md not found for skill '{skill_name}'"}, ensure_ascii=False)
    
    try:
        with open(skill_md_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        front_matter_match = re.search(r'^---\s*\n.*?\n---\s*\n', content, re.DOTALL)
        
        if front_matter_match:
            body_content = content[front_matter_match.end():]
        else:
            body_content = content
        
        body_content = body_content.strip()
        
        return json.dumps({
            "name": skill_name,
            "content": body_content
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({"error": f"Error loading skill content: {str(e)}"}, ensure_ascii=False)


SKILL_TOOL_FUNCTIONS = {
    "list_available_skills": list_available_skills,
    "load_skill_content": load_skill_content,
}
