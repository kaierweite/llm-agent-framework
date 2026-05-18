from typing import Callable, List, Tuple, Optional


class ChatHistory:
    def __init__(self, llm_caller: Callable[[list], str], summary_prompt_getter: Callable[[], str]):
        self._conversation_history: List[Tuple[str, str]] = []
        self._llm_caller = llm_caller
        self._summary_prompt_getter = summary_prompt_getter

    @property
    def conversation_history(self) -> List[Tuple[str, str]]:
        return self._conversation_history

    def add(self, user_input: str, assistant_response: str):
        self._conversation_history.append(("user", user_input))
        self._conversation_history.append(("assistant", assistant_response))

    def clear(self):
        self._conversation_history = []

    def replace_history(self, new_history: list):
        self._conversation_history = new_history

    def calculate_context_length(self) -> int:
        total_length = 0
        for role, content in self._conversation_history:
            total_length += len(role) + len(content)
        return total_length

    def should_summarize(self) -> bool:
        conversation_rounds = len(self._conversation_history) // 2
        context_length = self.calculate_context_length()

        return conversation_rounds >= 20 or context_length >= 30000

    def summarize_conversation(self) -> list:
        if len(self._conversation_history) < 4:
            return list(self._conversation_history)

        compress_point = int(len(self._conversation_history) * 0.7)
        keep_point = len(self._conversation_history) - compress_point

        history_to_summarize = self._conversation_history[:compress_point]
        history_to_keep = self._conversation_history[-keep_point:]

        summary_text = "请总结以下聊天记录的主要内容和关键信息：\n\n"
        for role, content in history_to_summarize:
            summary_text += f"{role}: {content}\n\n"

        # 限制摘要输入长度，避免超出 LLM 上下文窗口
        max_summary_input = 15000
        if len(summary_text) > max_summary_input:
            summary_text = summary_text[:max_summary_input] + "\n\n...（内容已截断）"

        messages = [
            {'role': 'system', 'content': self._summary_prompt_getter()},
            {'role': 'user', 'content': summary_text}
        ]

        try:
            summary = self._llm_caller(messages)
            if not summary or not summary.strip():
                return list(self._conversation_history)
        except Exception as e:
            print(f"[ChatHistory] 摘要生成失败，保留原始历史: {e}")
            return list(self._conversation_history)

        new_history = [
            ("assistant", f"[历史对话摘要]\n{summary}")
        ]
        new_history.extend(history_to_keep)

        return new_history

    def build_messages(self, system_prompt: str, user_input: str = None) -> list:
        messages = []

        messages.append({
            "role": "system",
            "content": system_prompt
        })

        for role, content in self._conversation_history:
            messages.append({"role": role, "content": content})

        if user_input:
            messages.append({"role": "user", "content": user_input})

        return messages
