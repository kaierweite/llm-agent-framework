import os
import json
import re

from ..llm.client import LLMClient
from ..logging.logger import ChatLogger
from .history import ChatHistory
from .redis_history import RedisChatHistory
from .memory_rules import MemoryRuleEngine
from .prompts import PromptManager
from ..tools.registry import ToolRegistry
from llm_agent import PROJECT_ROOT

DEFAULT_LOG_DIR = os.path.join(PROJECT_ROOT, "logs")


class ChatClientWithSkills:
    def __init__(self, env_path: str):
        self.env_vars = self.load_env(env_path)
        self.current_skill_content = None

        log_dir = self.env_vars.get('LOG_FILE_PATH', DEFAULT_LOG_DIR)
        if not os.path.isabs(log_dir):
            log_dir = os.path.join(os.path.dirname(os.path.abspath(env_path)), log_dir)
        self.log_dir = os.path.expanduser(log_dir)

        self.llm = LLMClient.from_env(self.env_vars)
        self.logger = ChatLogger(self.log_dir)

        self.prompts = PromptManager(
            tools={},
            get_skill_content=lambda: self.current_skill_content
        )

        self.tool_registry = ToolRegistry(
            api_key=self.env_vars.get('ANYTHINGLLM_API_KEY'),
            workspace_slug=self.env_vars.get('ANYTHINGLLM_WORKSPACE_SLUG', 'AI'),
            logger=self.logger,
            on_skill_loaded=self._on_skill_loaded
                )

        self.prompts.set_tools(self.tool_registry.get_tools())

        # 尝试使用 RedisChatHistory，Redis 不可用时回退到 ChatHistory
        self.history = self._create_history_backend()
        self.memory_rules = MemoryRuleEngine()

        self.logger.cleanup_old_logs()

    def _create_history_backend(self):
        """创建历史管理后端：优先 Redis，回退内存。"""
        try:
            from llm_agent.redis_client import get_redis
            redis = get_redis()
            redis.ping()
            # CLI 模式使用固定 user_id
            return RedisChatHistory(
                user_id="cli_user",
                session_id="cli_session",
                llm_caller=self.llm.call_llm,
                summary_prompt_getter=PromptManager.get_summary_system_prompt,
            )
        except Exception:
            print("[agent] Redis 不可用，使用内存历史管理")
            return ChatHistory(
                llm_caller=self.llm.call_llm,
                summary_prompt_getter=PromptManager.get_summary_system_prompt,
            )

    def _on_skill_loaded(self, content: str):
        self.current_skill_content = content
        self.prompts.invalidate_cache()

    @property
    def base_url(self): return self.llm.base_url

    @property
    def api_key(self): return self.llm.api_key

    @property
    def model(self): return self.llm.model

    @property
    def tool_functions(self): return self.tool_registry.get_tool_functions()

    @property
    def tools(self): return self.tool_registry.get_tools()

    @property
    def conversation_history(self): return self.history.conversation_history

    def load_env(self, env_path: str) -> dict:
        env_vars = {}
        if not os.path.exists(env_path):
            print(f"Warning: {env_path} not found")
            return env_vars
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
        return env_vars

    def stream_chat(self, user_input: str) -> str:
        if self.should_summarize():
            print("\n[检测到上下文过长，开始压缩对话历史...]")
            self.history.replace_history(self.history.summarize_conversation())
            print("[对话历史压缩完成]\n")

        messages = self.build_messages(user_input)
        return self.llm.call_llm(messages)

    def parse_tool_call(self, response: str) -> tuple:
        tool_calls = []
        clean_response = response

        function_call_pattern = r'<function_calls>\s*(\[.*?\])\s*</function_calls>'
        match = re.search(function_call_pattern, response, re.DOTALL)

        if match:
            try:
                tool_calls = json.loads(match.group(1))
                clean_response = response[:match.start()].strip()
            except json.JSONDecodeError:
                pass

                return tool_calls, clean_response

    def execute_tool_call(self, tool_calls: list) -> str:
        results = []
        tool_functions = self.tool_registry.get_tool_functions()

        for tool_call in tool_calls:
            tool_name = tool_call.get('name')
            parameters = tool_call.get('parameters', {})

            if tool_name in tool_functions:
                tool_func = tool_functions[tool_name]
                try:
                    if parameters:
                        result = tool_func(**parameters)
                    else:
                        result = tool_func()
                    results.append(f"[{tool_name}] {result}")
                except Exception as e:
                    results.append(f"[{tool_name}] 错误: {str(e)}")
            else:
                results.append(f"[{tool_name}] 工具未找到")

        return "\n\n".join(results)

    def handle_tool_calls_and_respond(self, user_input: str, tool_calls: list, clean_response: str) -> bool:
        tool_result = self.execute_tool_call(tool_calls)

        is_skill_load = any(call.get('name') == 'load_skill_content' for call in tool_calls)
        is_weather_query = any(call.get('name') == 'get_weather' for call in tool_calls)

        if is_weather_query:
            self.add_to_history(user_input, f"工具执行结果:\n{tool_result}")
            follow_up_messages = self.build_messages(
                f"天气查询结果已返回，请根据以下天气数据，用自然、友好的方式向用户介绍天气情况。包含温度、天气状况、穿衣建议等实用信息。\n\n天气数据:\n{tool_result}"
            )
            final_response = self.llm.call_llm(follow_up_messages)
            final_response = self.llm.strip_tool_call_tags(final_response)
            self.add_to_history(user_input, final_response)
            print(f"\n{final_response}")
            return True

        if is_skill_load:
            try:
                skill_data = json.loads(tool_result)
                if 'content' in skill_data:
                    self.current_skill_content = skill_data['content']
                    self.prompts.invalidate_cache()
                    self.add_to_history(user_input, f"已加载技能: {skill_data.get('name')}\n工具执行结果:\n{tool_result}")

                    follow_up_messages = self.build_messages(
                        f"技能已成功加载！现在你需要根据以下技能内容，生成用户请求的具体内容。\n\n【重要】请严格按照技能规则生成实际内容，不要复制或解释技能说明，直接输出用户需要的最终结果。\n\n技能内容:\n{self.current_skill_content}\n\n用户请求: {user_input}\n\n请立即生成结果，直接输出生成的公文内容，不要添加任何解释。"
                    )

                    final_response = self.llm.call_llm(follow_up_messages)
                    final_response = self.llm.strip_tool_call_tags(final_response)

                    print(final_response)

                    self.add_to_history(user_input, final_response)
                    return True
            except json.JSONDecodeError:
                pass

        self.add_to_history(user_input, clean_response + f"\n\n{tool_result}")

        follow_up_messages = self.build_messages(
            f"工具执行结果:\n{tool_result}\n\n请根据工具执行结果回答用户问题。"
        )

        result = self.llm.call_llm(follow_up_messages)
        result = self.llm.strip_tool_call_tags(result)

        print(result)

        return result

    def add_to_history(self, user_input: str, assistant_response: str,
                       tool_calls=None, model=None, usage=None, latency_ms=None):
        self.history.add(user_input, assistant_response)
        self.logger.write_to_log(user_input, assistant_response,
                                 tool_calls=tool_calls, model=model,
                                 usage=usage, latency_ms=latency_ms)

    def clear_history(self):
        self.history.clear()

    def clear_skill(self):
        self.current_skill_content = None
        self.prompts.invalidate_cache()

    def get_status(self) -> dict:
        return {
            "conversation_history": self.history.conversation_history,
            "context_length": self.history.calculate_context_length(),
            "should_summarize": self.should_summarize(),
            "log_dir": self.log_dir,
            "has_skill": bool(self.current_skill_content),
        }

    def search_history(self, query: str) -> str:
        return self.logger.search_in_log_file(query)

    def build_messages(self, user_input: str = None) -> list:
        system_prompt = self.prompts.get_system_prompt()
        return self.history.build_messages(system_prompt, user_input)

    def should_summarize(self) -> bool:
        return self.history.should_summarize()

    def summarize_conversation(self) -> list:
        return self.history.summarize_conversation()

    @staticmethod
    def should_use_search(user_input: str) -> bool:
        return user_input.strip().lower().startswith('/search')
