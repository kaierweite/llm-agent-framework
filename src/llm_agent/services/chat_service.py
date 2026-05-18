from typing import Optional, List, Tuple

from sqlalchemy import func, desc, or_
from sqlalchemy.orm import Session

from llm_agent.models.conversation import Conversation
from llm_agent.models.message import Message


class ChatError(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def create_conversation(
    db: Session,
    user_id: str,
    title: Optional[str] = None,
    knowledge_base_id: Optional[str] = None,
) -> Conversation:
    conversation = Conversation(
        user_id=user_id,
        title=title or "新对话",
        knowledge_base_id=knowledge_base_id,
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def list_conversations(
    db: Session,
    user_id: str,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[list, int]:
    total = (
        db.query(func.count(Conversation.id))
        .filter(Conversation.user_id == user_id)
        .scalar()
    )

    rows = (
        db.query(
            Conversation,
            func.count(Message.id).label("message_count"),
        )
        .outerjoin(Message, Message.conversation_id == Conversation.id)
        .filter(Conversation.user_id == user_id)
        .group_by(Conversation.id)
        .order_by(desc(Conversation.updated_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = []
    for conv, msg_count in rows:
        items.append({
            "id": conv.id,
            "title": conv.title,
            "knowledge_base_id": getattr(conv, "knowledge_base_id", None),
            "message_count": msg_count,
            "created_at": conv.created_at,
            "updated_at": conv.updated_at,
        })

    return items, total


def get_conversation(
    db: Session,
    user_id: str,
    conversation_id: str,
) -> Optional[Conversation]:
    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
        .first()
    )
    return conversation


def delete_conversation(
    db: Session,
    user_id: str,
    conversation_id: str,
) -> bool:
    conversation = get_conversation(db, user_id, conversation_id)
    if not conversation:
        return False
    db.delete(conversation)
    db.commit()
    return True


def save_message(
    db: Session,
    conversation_id: str,
    role: str,
    content: str,
    token_count: Optional[int] = None,
    latency_ms: Optional[int] = None,
    tool_calls: Optional[list] = None,
) -> Message:
    message = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        token_count=token_count,
        latency_ms=latency_ms,
        tool_calls=tool_calls,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def save_message_batch(
    db: Session,
    conversation_id: str,
    messages_data: List[dict],
) -> List[Message]:
    """批量保存消息，减少提交次数。"""
    if not messages_data:
        return []
    
    messages = []
    for data in messages_data:
        msg = Message(
            conversation_id=conversation_id,
            role=data["role"],
            content=data["content"],
            token_count=data.get("token_count"),
            latency_ms=data.get("latency_ms"),
            tool_calls=data.get("tool_calls"),
        )
        db.add(msg)
        messages.append(msg)
    
    db.commit()
    for msg in messages:
        db.refresh(msg)
    return messages


def get_history(
    db: Session,
    conversation_id: str,
    limit: Optional[int] = None,
) -> List[Message]:
    query = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )

    if limit is not None:
        all_msgs = query.all()
        return all_msgs[-limit:] if len(all_msgs) > limit else all_msgs

    return query.all()


def update_conversation_title(
    db: Session,
    user_id: str,
    conversation_id: str,
    new_title: str,
) -> Optional[Conversation]:
    conversation = get_conversation(db, user_id, conversation_id)
    if not conversation:
        return None
    conversation.title = new_title
    db.commit()
    db.refresh(conversation)
    return conversation


def delete_messages_by_ids(
    db: Session,
    conversation_id: str,
    message_ids: List[str],
) -> int:
    if not message_ids:
        return 0
    count = (
        db.query(Message)
        .filter(
            Message.conversation_id == conversation_id,
            Message.id.in_(message_ids),
        )
        .delete(synchronize_session=False)
    )
    db.commit()
    return count


def search_messages(
    db: Session,
    user_id: str,
    query: str,
    limit: int = 20,
    offset: int = 0,
) -> Tuple[list, int]:
    """搜索对话标题和消息内容，按对话分组返回"""
    if not query or not query.strip():
        return [], 0

    keyword = f"%{query.strip()}%"

    # 分两步：先找匹配的对话 ID，再查对话
    # 1) 标题匹配的对话 ID
    title_ids = [
        r[0] for r in
        db.query(Conversation.id)
        .filter(Conversation.user_id == user_id, Conversation.title.like(keyword))
        .all()
    ]

    # 2) 消息内容匹配的对话 ID
    content_ids = [
        r[0] for r in
        db.query(Message.conversation_id)
        .join(Conversation, Conversation.id == Message.conversation_id)
        .filter(Conversation.user_id == user_id, Message.content.like(keyword))
        .distinct()
        .all()
    ]

    # 合并去重
    conv_id_set = set(title_ids) | set(content_ids)
    if not conv_id_set:
        return [], 0

    total = len(conv_id_set)

    # 按最新消息时间排序，分页
    conv_rows = (
        db.query(Conversation)
        .filter(Conversation.id.in_(list(conv_id_set)))
        .order_by(desc(Conversation.updated_at))
        .offset(offset)
        .limit(limit)
        .all()
    )

    items = []
    for conv in conv_rows:
        # 获取该对话中匹配的消息（最多 5 条）
        matched_msgs = (
            db.query(Message)
            .filter(
                Message.conversation_id == conv.id,
                Message.content.like(keyword),
            )
            .order_by(Message.created_at.asc())
            .limit(5)
            .all()
        )

        messages_data = []
        for msg in matched_msgs:
            highlight = _make_highlight(msg.content, query.strip())
            messages_data.append({
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at.isoformat(),
                "highlight": highlight,
            })

        # 如果标题匹配但没有消息匹配，给一个标题匹配提示
        if conv.title and conv.title.lower().find(query.strip().lower()) != -1 and not messages_data:
            messages_data.append({
                "id": None,
                "role": "system",
                "content": conv.title,
                "created_at": conv.updated_at.isoformat(),
                "highlight": conv.title,
            })

        items.append({
            "conversation_id": conv.id,
            "conversation_title": conv.title,
            "messages": messages_data,
        })

    return items, total


def export_conversation_markdown(
    db: Session,
    user_id: str,
    conversation_id: str,
) -> Optional[str]:
    """导出对话为 Markdown 格式，返回 Markdown 字符串"""
    conv = get_conversation(db, user_id, conversation_id)
    if not conv:
        return None

    messages = get_history(db, conversation_id)

    lines = [f"# {conv.title}\n"]
    lines.append(f"**导出时间**：{__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    lines.append("---\n")

    for msg in messages:
        if msg.role == "user":
            lines.append("## 👤 用户\n")
        elif msg.role == "assistant":
            lines.append("## 🤖 助手\n")
        else:
            lines.append(f"## {msg.role}\n")
        lines.append(f"{msg.content or ''}\n")
        lines.append("---\n")

    return "\n".join(lines)


def _make_highlight(content: str, keyword: str) -> str:
    """从消息内容中提取包含关键词的片段，前后各保留 60 字符"""
    lower_content = content.lower()
    lower_keyword = keyword.lower()
    pos = lower_content.find(lower_keyword)

    if pos == -1:
        # 关键词不在原文中（理论上不会发生），返回前 120 字符
        return content[:120] + ("..." if len(content) > 120 else "")

    start = max(0, pos - 60)
    end = min(len(content), pos + len(keyword) + 60)
    snippet = content[start:end]

    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(content) else ""

    return prefix + snippet + suffix


def delete_messages_from(
    db: Session,
    conversation_id: str,
    from_message_id: str,
) -> int:
    """删除 from_message_id（含）之后的所有消息，返回删除数量"""
    target = db.query(Message).filter(
        Message.id == from_message_id,
        Message.conversation_id == conversation_id,
    ).first()
    if not target:
        return 0

    count = (
        db.query(Message)
        .filter(
            Message.conversation_id == conversation_id,
            Message.created_at >= target.created_at,
        )
        .delete(synchronize_session=False)
    )
    db.commit()
    return count


def edit_message_content(
    db: Session,
    conversation_id: str,
    message_id: str,
    new_content: str,
) -> Optional[Message]:
    """编辑一条 user 消息的内容，返回编辑后的消息；若消息不存在或非 user 则返回 None"""
    msg = db.query(Message).filter(
        Message.id == message_id,
        Message.conversation_id == conversation_id,
        Message.role == "user",
    ).first()
    if not msg:
        return None
    msg.content = new_content
    db.commit()
    db.refresh(msg)
    return msg
