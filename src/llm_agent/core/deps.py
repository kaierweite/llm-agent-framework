from typing import Optional

from llm_agent.config import settings
from llm_agent.core.chat_engine import ChatEngine

_engine: Optional[ChatEngine] = None


def get_chat_engine() -> ChatEngine:
    global _engine
    if _engine is None:
        _engine = ChatEngine(settings)
    return _engine
