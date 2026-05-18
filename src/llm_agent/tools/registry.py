import json
import re

from . import TOOL_DEFINITIONS, TOOL_FUNCTIONS, list_available_skills, load_skill_content
from .network_tools import query_anythingllm, list_anythingllm_documents


class ToolRegistry:
    def __init__(self, api_key: str, workspace_slug: str, logger, on_skill_loaded=None):
        self._api_key = api_key
        self._workspace_slug = workspace_slug
        self._logger = logger
        self._on_skill_loaded = on_skill_loaded

        self._tools = TOOL_DEFINITIONS.copy()
        self._tool_functions = TOOL_FUNCTIONS.copy()

        self._add_search_tool()
        self._add_anythingllm_tool()
        self._add_skill_tools()

    def update_workspace_slug(self, new_slug: str):
        """动态更新 AnythingLLM workspace slug，使工具指向当前对话绑定的知识库。"""
        if new_slug and new_slug != self._workspace_slug:
            self._workspace_slug = new_slug
            # 重新注册 AnythingLLM 工具，使用新的 slug
            self._add_anythingllm_tool()

    def get_tools(self) -> dict:
        return self._tools

    def get_tool_functions(self) -> dict:
        return self._tool_functions

    def get_tool_functions_snapshot(self, workspace_slug: str = None) -> dict:
        """返回 tool_functions 的快照。如果指定了 workspace_slug，使用该 slug 创建 AnythingLLM 工具，
        而不修改内部共享状态，从而避免并发请求间的竞态条件。"""
        snapshot = dict(self._tool_functions)
        if workspace_slug and workspace_slug != self._workspace_slug:
            api_key = self._api_key
            snapshot['anythingllm_query'] = lambda query, _k=api_key, _s=workspace_slug: query_anythingllm(query, _k, _s)
            snapshot['anythingllm_list_documents'] = lambda _k=api_key, _s=workspace_slug: list_anythingllm_documents(_k, _s)
        return snapshot

    def _add_search_tool(self):
        self._tools['search_chat_history'] = {
            "type": "function",
            "function": {
                "name": "search_chat_history",
                "description": "搜索聊天历史记录。当用户想要查找之前的聊天内容，或表达'查找聊天历史'的意思时调用此工具。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "用户的搜索查询关键词"
                        }
                    },
                    "required": ["query"]
                }
            }
        }
        self._tool_functions['search_chat_history'] = lambda query: self._logger.search_in_log_file(query)

    def _add_anythingllm_tool(self):
        self._tools['anythingllm_query'] = {
            "type": "function",
            "function": {
                "name": "anythingllm_query",
                "description": "查询 AnythingLLM 知识库中的内容。当用户想要查询AnythingLLM中存储的文档、知识库内容时调用此工具。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "要查询的消息内容"
                        }
                    },
                    "required": ["query"]
                }
            }
        }
        self._tools['anythingllm_list_documents'] = {
            "type": "function",
            "function": {
                "name": "anythingllm_list_documents",
                "description": "列出 AnythingLLM 知识库工作区中的所有文档。当用户想要查看仓库/知识库/文档仓库中有哪些文件、有多少文件、列出文件列表时调用此工具。",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        }
        api_key = self._api_key
        workspace_slug = self._workspace_slug
        self._tool_functions['anythingllm_query'] = lambda query: query_anythingllm(query, api_key, workspace_slug)
        self._tool_functions['anythingllm_list_documents'] = lambda: list_anythingllm_documents(api_key, workspace_slug)

    def _add_skill_tools(self):
        skills_json = list_available_skills()
        try:
            skills_data = json.loads(skills_json)
            skills_list = skills_data.get('skills', [])
        except json.JSONDecodeError:
            skills_list = []

        skill_keywords = []
        for skill in skills_list:
            skill_name = skill.get('name', '')
            skill_desc = skill.get('description', '')

            desc_match = re.search(r'触发词[：:]\s*(.+)', skill_desc)
            if desc_match:
                keywords = desc_match.group(1).split('、')
                for kw in keywords:
                    kw = kw.strip().strip('"').strip("'")
                    if kw:
                        skill_keywords.append((kw, skill_name))

        keywords_str = ", ".join([kw for kw, _ in skill_keywords])

        self._tools['load_skill_content'] = {
            "type": "function",
            "function": {
                "name": "load_skill_content",
                "description": f"加载指定技能的内容，当需要使用某个技能时调用此函数获取技能详情。根据可用技能列表（{keywords_str}）判断用户需要使用哪个技能。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "skill_name": {
                            "type": "string",
                            "description": "要加载的技能名称，从可用技能列表中选择"
                        }
                    },
                    "required": ["skill_name"]
                }
            }
        }

        on_skill_loaded = self._on_skill_loaded

        def load_skill_content_wrapper(skill_name: str) -> str:
            result = load_skill_content(skill_name)
            try:
                skill_data = json.loads(result)
                if 'content' in skill_data and on_skill_loaded:
                    on_skill_loaded(skill_data['content'])
            except json.JSONDecodeError:
                pass
            return result

        self._tool_functions['load_skill_content'] = load_skill_content_wrapper
