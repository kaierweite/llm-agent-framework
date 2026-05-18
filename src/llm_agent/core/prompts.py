import json
from typing import Callable, Optional

from ..tools import list_available_skills


class PromptManager:
    def __init__(self, tools: dict, get_skill_content: Callable[[], Optional[str]]):
        self._tools = tools
        self._get_skill_content = get_skill_content
        self._system_prompt_cache = None
        self._system_prompt_dirty = True

    def set_tools(self, tools: dict):
        self._tools = tools
        self.invalidate_cache()

    def invalidate_cache(self):
        self._system_prompt_dirty = True

    def get_system_prompt(self) -> str:
        if not self._system_prompt_dirty and self._system_prompt_cache:
            return self._system_prompt_cache

        tools_str = json.dumps(self._tools, ensure_ascii=False, indent=2)

        skills_json = list_available_skills()
        try:
            skills_data = json.loads(skills_json)
            skills_list = skills_data.get('skills', [])
        except json.JSONDecodeError:
            skills_list = []

        skills_prompt = json.dumps({"skills": skills_list}, ensure_ascii=False)

        current_skill_content = self._get_skill_content()

        skill_context = ""
        if current_skill_content:
            skill_context = f"""
<skill_reference>
技能规则（仅供参考，不要复制）:
{current_skill_content}
</skill_reference>

<output_required>
【输出要求】
1. 根据用户的具体请求，按照技能规则生成对应的内容
2. 【禁止】复制或返回上面的技能规则内容
3. 【必须】直接输出最终结果，不要添加任何解释
</output_required>
"""

        result = f"""
你是一个具有工具调用能力的AI助手。

可用技能列表（JSON格式）:
{skills_prompt}
{skill_context}

你可以调用以下工具来完成各种任务：

可用工具列表：
{tools_str}

工具调用格式：
当你需要调用工具时，请使用JSON格式输出，格式如下：
<function_calls>
[
  {{
    "name": "工具名称",
    "parameters": {{
      "参数名": "参数值"
    }}
  }}
]
</function_calls>

注意事项：
1. 如果用户的请求需要调用工具才能完成，请直接输出工具调用JSON，不要输出其他任何内容
2. 如果用户的请求不需要调用工具，可以直接回答
3. 工具调用必须严格按照上述JSON格式，用<function_calls>和</function_calls>包裹
4. 列出文件列表时，请使用 "." 表示当前目录
5. 如果用户询问天气（如某地天气怎么样、某地气温多少），请直接调用 get_weather 工具，city参数填写城市名称（如"成都"、"达州"、"青城山"）
6. 如果用户输入以 "/search" 开头，或者用户表达了"查找聊天历史"这个意思，你应该调用 search_chat_history 工具来搜索聊天记录
7. 如果用户提到"文档仓库"、"文件仓库"、"仓库"、"知识库"、AnythingLLM相关内容，或者询问"仓库里有什么"、"查询仓库"等，你应该调用 anythingllm_query 工具来查询AnythingLLM知识库
8. 如果用户的请求涉及到公文撰写、通知生成、报告编写等，请先调用 load_skill_content 工具加载对应技能内容，然后【立即生成用户需要的实际内容】，不要复制或解释技能说明，直接输出最终结果
9. 技能加载后的响应必须是生成的公文内容，【禁止】返回技能说明、工具返回结果或任何解释性文字
10. 如果工具执行结果表明任务尚未完成，你可以继续调用其他工具来完成任务
11. 当所有必要信息都已收集完毕后，请综合所有工具调用结果，直接给出最终回答
12. 最多连续调用5次工具，之后必须给出最终回答，不要继续调用工具
13. 如果已有足够信息回答用户，请直接输出最终回答，不要调用工具

【回复格式规则】
- 回复简洁、美观
- 只列出关键信息，不要添加额外的总结或解释
- 【绝对禁止】在最终回答中输出 <function_calls> 标签、JSON 工具调用格式或任何代码块包裹的工具调用。工具调用只在需要执行操作时由系统自动处理，你的最终回答必须是纯自然语言
        """.strip()

        self._system_prompt_cache = result
        self._system_prompt_dirty = False
        return result

    @staticmethod
    def get_summary_system_prompt() -> str:
        return """你是一个对话总结助手。你的任务是将聊天记录进行压缩总结，保留关键信息。

请按照以下格式输出总结：
1. 用户意图：用户的核心需求或问题
2. 关键信息：对话中涉及的重要信息、数据、结论等
3. 执行结果：如有工具调用，记录执行结果

注意：
- 保留所有关键信息
- 保持信息的准确性和完整性
- 使用简洁的语言
- 不要遗漏重要细节
"""
