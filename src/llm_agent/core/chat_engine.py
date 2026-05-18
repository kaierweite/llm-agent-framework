import time
import threading
from contextvars import ContextVar
from typing import Callable, Optional

from sqlalchemy.orm import Session

from llm_agent.config import Settings
from llm_agent.llm.client import LLMClient, ContextLengthExceededError
from llm_agent.core.history import ChatHistory
from llm_agent.core.redis_history import RedisChatHistory
from llm_agent.core.memory_rules import MemoryRuleEngine
from llm_agent.core.session_init import init_session_summary, async_load_window
from llm_agent.core.prompts import PromptManager
from llm_agent.core.tool_executor import (
    parse_tool_call, execute_tool_calls, execute_tool_calls_async,
    MAX_TOOL_ROUNDS, MAX_TOTAL_TOOL_TIME,
)
from llm_agent.tools.registry import ToolRegistry
from llm_agent.logging.logger import ChatLogger
from llm_agent.models.conversation import Conversation
from llm_agent.models.knowledge_base import KnowledgeBase
from llm_agent.services import chat_service, knowledge_service

# 每个协程/调用独立的 conversation_id，避免异步竞态
_active_conv_var: ContextVar[Optional[str]] = ContextVar('_active_conv_var', default=None)


class ChatEngine:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._skill_content_by_conv: dict[str, str] = {}
        self._skill_lock = threading.Lock()

        self.logger = ChatLogger(settings.log_file_path)
        self.prompts = PromptManager(tools={}, get_skill_content=self._get_current_skill_content)
        self.memory_rules = MemoryRuleEngine()
        self._histories: dict[str, RedisChatHistory] = {}

        self._llm_config_snapshot: tuple = ()
        self._tool_config_snapshot: tuple = ()
        self.llm = None
        self.tool_registry = None
        self._sync_config()

    # ── 配置热更新 ──

    def _sync_config(self):
        llm_snap = (self._settings.llm_base_url, self._settings.llm_api_key, self._settings.llm_model)
        tool_snap = (self._settings.anythingllm_api_key, self._settings.anythingllm_workspace_slug)

        if llm_snap != self._llm_config_snapshot:
            self.llm = LLMClient(base_url=self._settings.llm_base_url, api_key=self._settings.llm_api_key, model=self._settings.llm_model)
            self._llm_config_snapshot = llm_snap

        if tool_snap != self._tool_config_snapshot or self.tool_registry is None:
            self.tool_registry = ToolRegistry(
                api_key=self._settings.anythingllm_api_key,
                workspace_slug=self._settings.anythingllm_workspace_slug,
                logger=self.logger,
                on_skill_loaded=self._on_skill_loaded,
            )
            self.prompts.set_tools(self.tool_registry.get_tools())
            self._tool_config_snapshot = tool_snap

        # ── 技能内容隔离 ──

    @property
    def _active_conversation_id(self) -> Optional[str]:
        return _active_conv_var.get()

    @_active_conversation_id.setter
    def _active_conversation_id(self, value: Optional[str]):
        _active_conv_var.set(value)

    def _get_current_skill_content(self) -> Optional[str]:
        conv_id = self._active_conversation_id
        if not conv_id:
            return None
        with self._skill_lock:
            return self._skill_content_by_conv.get(conv_id)

    def _on_skill_loaded(self, content: str):
        conv_id = self._active_conversation_id
        if conv_id:
            with self._skill_lock:
                self._skill_content_by_conv[conv_id] = content
                if len(self._skill_content_by_conv) > 200:
                    keys = list(self._skill_content_by_conv.keys())
                    for k in keys[:100]:
                        del self._skill_content_by_conv[k]
            self.prompts.invalidate_cache()

    # ── 历史管理 ──

    def _get_or_create_history(self, conversation_id: str, user_id: str = None, db_session=None) -> RedisChatHistory:
        if conversation_id not in self._histories:
            uid = user_id or conversation_id
            history = RedisChatHistory(user_id=uid, session_id=conversation_id, llm_caller=self.llm.call_llm,
                                       summary_prompt_getter=PromptManager.get_summary_system_prompt, db_session=db_session)
            self._histories[conversation_id] = history
            if db_session:
                init_session_summary(uid, conversation_id, db_session)
                async_load_window(uid, conversation_id, db_session)
        return self._histories[conversation_id]

    def _build_tool_context(self, knowledge_context: str | None) -> str:
        """统一构建工具上下文（知识库内容），供 _build_messages 使用。"""
        context_parts = []
        if knowledge_context:
            truncated = knowledge_context[:self._settings.context_max_chars]
            if len(knowledge_context) > self._settings.context_max_chars:
                truncated += "...（内容已截断）"
            context_parts.append(f"--- 以下是知识库检索到的相关内容，请优先参考以下内容回答用户问题 ---\n{truncated}\n--- 知识库内容结束 ---")
        return "\n\n".join(context_parts)

    def _build_messages(self, history: ChatHistory, user_input: str = None, knowledge_context: str = None) -> list:
        system_prompt = self.prompts.get_system_prompt()
        tool_context = self._build_tool_context(knowledge_context)
        if tool_context:
            system_prompt += f"\n\n{tool_context}"
        return history.build_messages(system_prompt, user_input)

    @staticmethod
    def _truncate_messages_for_retry(messages: list) -> list:
        if len(messages) <= 2:
            return messages
        system_msgs = [m for m in messages if m.get("role") == "system"]
        non_system = [m for m in messages if m.get("role") != "system"]
        keep = max(8, len(non_system) // 2)
        return system_msgs + non_system[-keep:]

    # ── 知识库 ──

    def _get_workspace_slug_for_conversation(self, db: Session, conversation_id: str) -> str | None:
        """获取对话绑定的知识库 workspace slug，不修改共享状态。"""
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conversation or not conversation.knowledge_base_id:
            return None
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == conversation.knowledge_base_id).first()
        return kb.anythingllm_workspace_slug if kb else None

    def _retrieve_knowledge_context(self, db: Session, conversation_id: str, user_message: str) -> tuple:
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conversation or not conversation.knowledge_base_id:
            return None, False
        try:
            result = knowledge_service.query_knowledge_base(db, conversation.user_id, conversation.knowledge_base_id, user_message)
            if not result or not result.strip():
                return None, False
            if len(result) <= 2000:
                return result, False
            return self._rerank_knowledge(result, user_message), False
        except Exception as e:
            print(f"Warning: 知识库检索失败 (conversation={conversation_id}): {e}")
            return None, True

    def _rerank_knowledge(self, raw_result: str, user_message: str, top_k: int = 3) -> str:
        separators = ["\n---\n", "\n\n---\n", "\n===\n", "\n\n", "\n"]
        cn_sentence_seps = ["。", "？", "！", "；", ".", "?", "!", ";"]

        chunks = [raw_result]
        for sep in separators:
            new_chunks = []
            for chunk in chunks:
                new_chunks.extend(chunk.split(sep))
            chunks = new_chunks

        refined_chunks = []
        for chunk in chunks:
            if len(chunk) > 800:
                sub_chunks = [chunk]
                for sep in cn_sentence_seps:
                    new_sub = []
                    for sc in sub_chunks:
                        new_sub.extend(sc.split(sep))
                    sub_chunks = new_sub
                refined_chunks.extend(sub_chunks)
            else:
                refined_chunks.append(chunk)
        chunks = refined_chunks

        seen = set()
        unique_chunks = []
        for c in chunks:
            c = c.strip()
            if c and c not in seen and len(c) > 20:
                seen.add(c)
                unique_chunks.append(c)

        if len(unique_chunks) <= top_k:
            return "\n\n---\n\n".join(unique_chunks)

        try:
            numbered = "\n".join(f"[片段{i+1}] {c[:300]}" for i, c in enumerate(unique_chunks))
            rerank_prompt = [
                {"role": "system", "content": f"你是一个文档片段筛选器。根据用户问题，判断每个片段的相关性。返回最相关的 {top_k} 个片段编号，用逗号分隔，如：1,3,5。只输出编号，不要解释。"},
                {"role": "user", "content": f"用户问题：{user_message}\n\n{numbered}"},
            ]
            response = self.llm.call_llm(rerank_prompt, stream=False)
            indices = []
            for token in response.split(","):
                token = token.strip().strip(".")
                if token.isdigit():
                    idx = int(token) - 1
                    if 0 <= idx < len(unique_chunks):
                        indices.append(idx)
            if indices:
                return "\n\n---\n\n".join([unique_chunks[i] for i in indices[:top_k]])
        except Exception:
            pass

        result = "\n\n---\n\n".join(unique_chunks)
        return result[:4000] + "...（内容已截断）" if len(result) > 4000 else result

    # ── 技能上下文 ──

    def _build_skill_followup_context(self, user_input: str) -> Optional[str]:
        skill_content = self._get_current_skill_content()
        if not skill_content:
            return None
        return (
            f"技能已成功加载！现在你需要根据以下技能内容，生成用户请求的具体内容。\n\n"
            f"【重要】请严格按照技能规则生成实际内容，不要复制或解释技能说明，直接输出用户需要的最终结果。\n\n"
            f"技能内容:\n{skill_content}\n\n"
            f"用户请求: {user_input}\n\n"
            f"请立即生成结果，直接输出生成的公文内容，不要添加任何解释。"
        )

        # ── 核心消息处理（同步 + 异步共用逻辑） ──

    def _run_tool_loop(
        self,
        history: ChatHistory,
        messages: list,
        user_message: str,
        knowledge_context: str | None,
        llm_caller: Callable,
        tool_functions: dict,
        on_chunk: Callable | None,
        on_tool_start: Callable | None,
        on_tool_result: Callable | None,
        on_tool_round: Callable | None,
    ) -> tuple[str, list]:
        """执行多轮工具调用循环，返回 (assistant_response, all_tool_calls_collector)。"""
        start_time = time.time()
        all_tool_calls_collector: list = []
        original_user_message = user_message
        tool_round = 0
        assistant_response = ''

        # 第 1 轮流式输出先缓冲，避免工具调用 JSON 泄露给前端
        _chunk_buffer: list[str] = []

        def _buffering_chunk(text: str):
            _chunk_buffer.append(text)

        try:
            response = llm_caller(messages, on_chunk=_buffering_chunk)
        except ContextLengthExceededError:
            messages = self._truncate_messages_for_retry(messages)
            _chunk_buffer.clear()
            response = llm_caller(messages, on_chunk=_buffering_chunk)

        tool_calls, clean_response = parse_tool_call(response)

        if tool_calls:
            # 是工具调用，丢弃缓冲的 JSON 片段
            _chunk_buffer.clear()
        else:
            # 不是工具调用，把缓冲的正常内容推给前端
            if on_chunk:
                for chunk in _chunk_buffer:
                    on_chunk(chunk)
            _chunk_buffer.clear()

        while tool_calls and tool_round < MAX_TOOL_ROUNDS:
            if time.time() - start_time > MAX_TOTAL_TOOL_TIME:
                break

            tool_round += 1
            if on_tool_round:
                on_tool_round(tool_round)

                        # 执行工具
            tool_calls_collector: list = []
            tool_result = execute_tool_calls(tool_calls, tool_functions, on_tool_start, on_tool_result, tool_calls_collector)
            all_tool_calls_collector.extend(tool_calls_collector)

            history.add(user_message, clean_response)

            skill_context = self._build_skill_followup_context(user_message)
            followup_input = skill_context or f"工具执行结果:\n{tool_result}\n\n请根据工具执行结果回答用户问题。如果任务尚未完成，可以继续调用工具。"
            messages = self._build_messages(history, followup_input, knowledge_context)

            try:
                response = llm_caller(messages)
            except ContextLengthExceededError:
                messages = self._truncate_messages_for_retry(messages)
                response = llm_caller(messages)

            tool_calls, clean_response = parse_tool_call(response)
            user_message = followup_input

        # 安全防护兜底
        if tool_calls and tool_round >= MAX_TOOL_ROUNDS and not clean_response:
            clean_response = "已达到最大工具调用轮次，以下是已收集到的结果。"
        elif tool_calls and time.time() - start_time > MAX_TOTAL_TOOL_TIME and not clean_response:
            clean_response = "工具调用总耗时超限，以下是已收集到的结果。"

        return clean_response, all_tool_calls_collector

    # ── 同步入口 ──

    def process_message(
        self, user_message: str, conversation_id: str, db: Session,
        on_chunk=None, on_tool_start=None, on_tool_result=None, on_tool_round=None,
    ) -> str:
        self._sync_config()
        self._active_conversation_id = conversation_id
        try:
            return self._process_message_inner(user_message, conversation_id, db, on_chunk, on_tool_start, on_tool_result, on_tool_round)
        except Exception as e:
            self.logger.error(f"消息处理失败 (conversation={conversation_id}): {e}")
            return "抱歉，AI 服务暂时不可用，请稍后再试。如果问题持续，请联系管理员。"
        finally:
            self._active_conversation_id = None

    def _process_message_inner(self, user_message, conversation_id, db, on_chunk, on_tool_start, on_tool_result, on_tool_round):
        conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        user_id = conv.user_id if conv else conversation_id
        history = self._get_or_create_history(conversation_id, user_id, db)
        knowledge_context, kb_failed = self._retrieve_knowledge_context(db, conversation_id, user_message)
        messages = self._build_messages(history, user_message, knowledge_context)

        start_time = time.time()
        original_user_message = user_message
        # 获取对话绑定的 workspace slug，传入快照方法，不修改共享状态
        target_slug = self._get_workspace_slug_for_conversation(db, conversation_id)
        tool_functions = self.tool_registry.get_tool_functions_snapshot(workspace_slug=target_slug)

        assistant_response, all_tool_calls = self._run_tool_loop(
            history, messages, user_message, knowledge_context,
            llm_caller=self.llm.call_llm, tool_functions=tool_functions,
            on_chunk=on_chunk, on_tool_start=on_tool_start, on_tool_result=on_tool_result, on_tool_round=on_tool_round,
        )

        latency_ms = int((time.time() - start_time) * 1000)

        if kb_failed:
            assistant_response += "\n\n知识库检索暂时不可用，以上为通用回答。"

        chat_service.save_message_batch(db, conversation_id, [
            {"role": "user", "content": original_user_message},
            {"role": "assistant", "content": assistant_response, "latency_ms": latency_ms,
             "tool_calls": all_tool_calls if all_tool_calls else None},
        ])

        history.add(original_user_message, assistant_response)
        self.memory_rules.process(original_user_message, history)
        return assistant_response

    # ── 异步入口 ──

    async def async_process_message(
        self, user_message: str, conversation_id: str, db: Session,
        on_chunk=None, on_tool_start=None, on_tool_result=None, on_tool_round=None,
    ) -> str:
        self._sync_config()
        self._active_conversation_id = conversation_id
        try:
            return await self._async_process_message_inner(user_message, conversation_id, db, on_chunk, on_tool_start, on_tool_result, on_tool_round)
        except Exception as e:
            self.logger.error(f"异步消息处理失败 (conversation={conversation_id}): {e}")
            return "抱歉，AI 服务暂时不可用，请稍后再试。如果问题持续，请联系管理员。"
        finally:
            self._active_conversation_id = None

    async def _async_run_tool_loop(
        self,
        history: ChatHistory,
        messages: list,
        user_message: str,
        knowledge_context: str | None,
        tool_functions: dict,
        on_chunk: Callable | None,
        on_tool_start: Callable | None,
        on_tool_result: Callable | None,
        on_tool_round: Callable | None,
    ) -> tuple[str, list]:
        """异步版：执行多轮工具调用循环，返回 (assistant_response, all_tool_calls_collector)。"""
        start_time = time.time()
        all_tool_calls_collector: list = []
        original_user_message = user_message
        tool_round = 0
        assistant_response = ''

        # ── 智能流式：正常文本边生成边推送，仅在检测到工具调用时缓冲 ──
        _chunk_buffer: list[str] = []
        _streaming_mode = "detecting"  # "detecting" | "streaming" | "buffering"

        def _smart_chunk(text: str):
            nonlocal _streaming_mode
            if _streaming_mode == "detecting":
                if text.lstrip().startswith("{"):
                    _streaming_mode = "buffering"
                    _chunk_buffer.append(text)
                else:
                    _streaming_mode = "streaming"
                    if on_chunk:
                        on_chunk(text)
            elif _streaming_mode == "streaming":
                if on_chunk:
                    on_chunk(text)
            else:  # buffering
                _chunk_buffer.append(text)

        def _reset_streaming():
            nonlocal _streaming_mode
            _chunk_buffer.clear()
            _streaming_mode = "detecting"

        try:
            response = await self.llm.async_call_llm(messages, on_chunk=_smart_chunk)
        except ContextLengthExceededError:
            messages = self._truncate_messages_for_retry(messages)
            _reset_streaming()
            response = await self.llm.async_call_llm(messages, on_chunk=_smart_chunk)

        tool_calls, clean_response = parse_tool_call(response)
        _reset_streaming()

        while tool_calls and tool_round < MAX_TOOL_ROUNDS:
            if time.time() - start_time > MAX_TOTAL_TOOL_TIME:
                break

            tool_round += 1
            if on_tool_round:
                on_tool_round(tool_round)

            tool_calls_collector: list = []
            tool_result = await execute_tool_calls_async(tool_calls, tool_functions, on_tool_start, on_tool_result, tool_calls_collector)
            all_tool_calls_collector.extend(tool_calls_collector)

            history.add(user_message, clean_response)

            skill_context = self._build_skill_followup_context(user_message)
            followup_input = skill_context or f"工具执行结果:\n{tool_result}\n\n请根据工具执行结果回答用户问题。如果任务尚未完成，可以继续调用工具。"
            messages = self._build_messages(history, followup_input, knowledge_context)

            _reset_streaming()
            try:
                response = await self.llm.async_call_llm(messages, on_chunk=_smart_chunk)
            except ContextLengthExceededError:
                messages = self._truncate_messages_for_retry(messages)
                _reset_streaming()
                response = await self.llm.async_call_llm(messages, on_chunk=_smart_chunk)

            tool_calls, clean_response = parse_tool_call(response)
            _reset_streaming()
            user_message = followup_input

        if tool_calls and tool_round >= MAX_TOOL_ROUNDS and not clean_response:
            clean_response = "已达到最大工具调用轮次，以下是已收集到的结果。"
        elif tool_calls and time.time() - start_time > MAX_TOTAL_TOOL_TIME and not clean_response:
            clean_response = "工具调用总耗时超限，以下是已收集到的结果。"

        return clean_response, all_tool_calls_collector

    async def _async_process_message_inner(self, user_message, conversation_id, db, on_chunk, on_tool_start, on_tool_result, on_tool_round):
        conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        user_id = conv.user_id if conv else conversation_id
        history = self._get_or_create_history(conversation_id, user_id, db)
        knowledge_context, kb_failed = self._retrieve_knowledge_context(db, conversation_id, user_message)
        messages = self._build_messages(history, user_message, knowledge_context)

        start_time = time.time()
        original_user_message = user_message
        target_slug = self._get_workspace_slug_for_conversation(db, conversation_id)
        tool_functions = self.tool_registry.get_tool_functions_snapshot(workspace_slug=target_slug)

        assistant_response, all_tool_calls = await self._async_run_tool_loop(
            history, messages, user_message, knowledge_context,
            tool_functions=tool_functions,
            on_chunk=on_chunk, on_tool_start=on_tool_start, on_tool_result=on_tool_result, on_tool_round=on_tool_round,
        )

        latency_ms = int((time.time() - start_time) * 1000)

        if kb_failed:
            assistant_response += "\n\n知识库检索暂时不可用，以上为通用回答。"

        chat_service.save_message_batch(db, conversation_id, [
            {"role": "user", "content": original_user_message},
            {"role": "assistant", "content": assistant_response, "latency_ms": latency_ms,
             "tool_calls": all_tool_calls if all_tool_calls else None},
        ])

        history.add(original_user_message, assistant_response)
        self.memory_rules.process(original_user_message, history)
        return assistant_response

    def get_tools(self) -> dict:
        return self.tool_registry.get_tools()
