import json
import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.orm import Session
from sqlalchemy import desc

from llm_agent.database import get_db
import llm_agent.database as _db_mod
from llm_agent.middleware.auth import get_current_user
from llm_agent.models.user import User
from llm_agent.models.message import Message
from llm_agent.api.schemas.conversation import (
    ConversationCreate,
    ConversationRename,
    MessageCreate,
)
from llm_agent.core.deps import get_chat_engine
from llm_agent.services import chat_service, knowledge_service
from llm_agent.services.kb_share_service import can_access
from llm_agent.services.audit_service import (
    log_action,
    ACTION_CONVERSATION_CREATE,
    ACTION_CONVERSATION_DELETE,
    ACTION_CONVERSATION_RENAME,
    ACTION_MESSAGE_FEEDBACK,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["对话"])


# ------------------------------------------------------------------
# 工具函数
# ------------------------------------------------------------------

def _conversation_response(conv) -> dict:
    return {
        "id": conv.id,
        "title": conv.title,
        "knowledge_base_id": getattr(conv, "knowledge_base_id", None),
        "created_at": conv.created_at.isoformat(),
        "updated_at": conv.updated_at.isoformat(),
    }


def _message_response(msg) -> dict:
    return {
        "id": msg.id,
        "role": msg.role,
        "content": msg.content,
        "token_count": msg.token_count,
        "latency_ms": msg.latency_ms,
        "tool_calls": getattr(msg, "tool_calls", None),
        "feedback": getattr(msg, "feedback", None),
        "created_at": msg.created_at.isoformat(),
    }


def _maybe_update_knowledge_base(db: Session, conv, knowledge_base_id: str | None):
    """更新对话的知识库绑定。knowledge_base_id=None 表示清除绑定（用户选择"无知识库"）。"""
    current_kb_id = getattr(conv, "knowledge_base_id", None)
    if current_kb_id != knowledge_base_id:
        conv.knowledge_base_id = knowledge_base_id
        db.commit()
        db.refresh(conv)


def _verify_conversation_owner(db: Session, user_id: str, conversation_id: str):
    conv = chat_service.get_conversation(db, user_id, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail={"code": 40401, "message": "Conversation not found"})
    return conv


def _sse_data(event: dict) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


# ------------------------------------------------------------------
# 异步流式生成器（三个流式路由共用）
# ------------------------------------------------------------------

async def _stream_generator(
    user_content: str,
    conversation_id: str,
    db_session_factory,
    request=None,
):
    """
    异步流式 SSE 生成器。

    架构：
    - LLM 调用通过 async_call_llm 在事件循环中异步执行（不阻塞线程）
    - 工具执行仍在 ThreadPoolExecutor 中（保持并行工具调用能力）
    - on_chunk 回调从事件循环线程调用，直接 put_nowait
    - on_tool_start/result 回调从线程池 worker 调用，用 call_soon_threadsafe 桥接
    - SSE 生成器从 asyncio.Queue 读取事件并 yield

    客户端断开检测：
    - 每次 yield 前检查 request.is_disconnected()
    - 客户端断开时取消引擎任务并关闭 session，避免资源泄漏
    """
    aq: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def on_chunk(text: str):
        aq.put_nowait(text)

    def on_tool_start(tool_name: str, arguments: dict, tool_call_id: str = ""):
        event = json.dumps({
            "type": "tool_call", "tool_call_id": tool_call_id,
            "name": tool_name, "arguments": arguments, "status": "running",
        }, ensure_ascii=False)
        loop.call_soon_threadsafe(aq.put_nowait, event)

    def on_tool_result(tool_name: str, result: str, success: bool, tool_call_id: str = ""):
        event = json.dumps({
            "type": "tool_result", "tool_call_id": tool_call_id,
            "name": tool_name, "result": result[:500],
            "status": "success" if success else "error",
        }, ensure_ascii=False)
        loop.call_soon_threadsafe(aq.put_nowait, event)

    def on_tool_round(round_num: int):
        event = json.dumps({
            "type": "tool_round", "round": round_num,
        }, ensure_ascii=False)
        loop.call_soon_threadsafe(aq.put_nowait, event)

    result_holder = {"reply": None, "error": None}
    thread_db = None
    task = None

    try:
        thread_db = db_session_factory()

        async def run_engine():
            try:
                engine = get_chat_engine()
                result_holder["reply"] = await engine.async_process_message(
                    user_message=user_content,
                    conversation_id=conversation_id,
                    db=thread_db,
                    on_chunk=on_chunk,
                    on_tool_start=on_tool_start,
                    on_tool_result=on_tool_result,
                    on_tool_round=on_tool_round,
                )
            except Exception as e:
                result_holder["error"] = str(e)

        task = asyncio.create_task(run_engine())

        while not task.done() or not aq.empty():
            if request and await request.is_disconnected():
                logger.info(f"客户端断开连接 (conversation={conversation_id})，取消引擎任务")
                task.cancel()
                break

            try:
                data = await asyncio.wait_for(aq.get(), timeout=0.2)
                try:
                    parsed = json.loads(data)
                    if isinstance(parsed, dict):
                        event_type = parsed.get("type", "chunk")
                        if event_type in ("tool_call", "tool_result", "tool_round"):
                            yield _sse_data(parsed)
                        else:
                            yield _sse_data({"type": "chunk", "content": data})
                    else:
                        yield _sse_data({"type": "chunk", "content": data})
                except (json.JSONDecodeError, TypeError):
                    yield _sse_data({"type": "chunk", "content": data})
            except asyncio.TimeoutError:
                continue

        if task and not task.done():
            try:
                await asyncio.wait_for(task, timeout=5.0)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                task.cancel()

        if result_holder["error"]:
            yield _sse_data({"type": "error", "content": result_holder["error"]})
        elif result_holder["reply"]:
            yield _sse_data({"type": "done", "content": result_holder["reply"]})

    except asyncio.CancelledError:
        logger.info(f"SSE 生成器被取消 (conversation={conversation_id})")
    except Exception as e:
        logger.error(f"SSE 生成器异常 (conversation={conversation_id}): {e}")
        yield _sse_data({"type": "error", "content": str(e)})
    finally:
        if thread_db is not None:
            try:
                if thread_db.is_active and thread_db.dirty:
                    thread_db.rollback()
                thread_db.close()
            except Exception:
                pass


# ------------------------------------------------------------------
# 搜索 & 导出（同步路由，无 LLM 调用）
# ------------------------------------------------------------------

@router.get("/search")
def search_messages(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items, total = chat_service.search_messages(db, user_id=current_user.id, query=q, limit=limit, offset=offset)
    return {"code": 0, "message": "success", "data": {"total": total, "items": items}}


@router.get("/conversations/{conversation_id}/export")
def export_conversation(
    conversation_id: str,
    format: str = Query("markdown"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    logging.info(f"[EXPORT] conversation_id={conversation_id} format={format} user={current_user.id}")
    if format != "markdown":
        raise HTTPException(status_code=400, detail="仅支持 markdown 格式")
    conv = chat_service.get_conversation(db, current_user.id, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")
    try:
        md_content = chat_service.export_conversation_markdown(db, user_id=current_user.id, conversation_id=conversation_id)
    except Exception as e:
        logging.exception("[EXPORT] 导出对话失败")
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")
    if md_content is None:
        raise HTTPException(status_code=404, detail="对话内容为空")
    filename = f"{conv.title or '对话'}.md"
    return Response(
        content=md_content.encode("utf-8"),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ------------------------------------------------------------------
# CRUD（同步路由，无 LLM 调用）
# ------------------------------------------------------------------

@router.post("/conversations", status_code=201)
def create_conversation(
    body: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 如果指定了知识库，验证用户是否有访问权（owner 或共享）
    if body.knowledge_base_id:
        kb = knowledge_service.get_knowledge_base(db, current_user.id, body.knowledge_base_id)
        if not kb:
            kb = knowledge_service.get_knowledge_base_by_id(db, body.knowledge_base_id)
        if not kb:
            raise HTTPException(status_code=404, detail={"code": 40401, "message": "Knowledge base not found"})
        # 非 owner 需要检查共享权限
        if kb.owner_id != current_user.id:
            share = can_access(db, body.knowledge_base_id, current_user.id)
            if not share:
                raise HTTPException(status_code=403, detail={"code": 40301, "message": "No access to this knowledge base"})

    conv = chat_service.create_conversation(db, user_id=current_user.id, title=body.title, knowledge_base_id=body.knowledge_base_id)
    log_action(db, ACTION_CONVERSATION_CREATE, user_id=current_user.id, user_email=current_user.email,
               resource_type="conversation", resource_id=conv.id,
               detail=f"创建对话: {conv.title}")
    return {"code": 0, "message": "success", "data": _conversation_response(conv)}


@router.get("/conversations")
def list_conversations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items, total = chat_service.list_conversations(db, user_id=current_user.id, page=page, page_size=page_size)
    return {"code": 0, "message": "success", "data": {"items": items, "total": total, "page": page, "page_size": page_size}}


@router.get("/conversations/{conversation_id}")
def get_conversation_detail(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conv = chat_service.get_conversation(db, current_user.id, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail={"code": 40401, "message": "Conversation not found"})
    messages = chat_service.get_history(db, conv.id)
    return {
        "code": 0, "message": "success",
        "data": {
            "id": conv.id, "title": conv.title,
            "knowledge_base_id": getattr(conv, "knowledge_base_id", None),
            "created_at": conv.created_at.isoformat(), "updated_at": conv.updated_at.isoformat(),
            "messages": [_message_response(m) for m in messages],
        },
    }


@router.put("/conversations/{conversation_id}")
def rename_conversation(
    conversation_id: str,
    body: ConversationRename,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conv = chat_service.update_conversation_title(db, current_user.id, conversation_id, body.title)
    if not conv:
        raise HTTPException(status_code=404, detail={"code": 40401, "message": "Conversation not found"})
    log_action(db, ACTION_CONVERSATION_RENAME, user_id=current_user.id, user_email=current_user.email,
               resource_type="conversation", resource_id=conversation_id,
               detail=f"重命名对话为: {body.title}")
    return {"code": 0, "message": "success", "data": _conversation_response(conv)}


@router.delete("/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    deleted = chat_service.delete_conversation(db, current_user.id, conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail={"code": 40401, "message": "Conversation not found"})
    log_action(db, ACTION_CONVERSATION_DELETE, user_id=current_user.id, user_email=current_user.email,
               resource_type="conversation", resource_id=conversation_id,
               detail=f"删除对话: {conversation_id}")
    return {"code": 0, "message": "Conversation deleted", "data": None}


# ------------------------------------------------------------------
# 同步发消息（非流式）
# ------------------------------------------------------------------

@router.post("/conversations/{conversation_id}/messages")
def send_message(
    conversation_id: str,
    body: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conv = _verify_conversation_owner(db, current_user.id, conversation_id)
    _maybe_update_knowledge_base(db, conv, body.knowledge_base_id)
    engine = get_chat_engine()
    reply = engine.process_message(user_message=body.content, conversation_id=conversation_id, db=db)
    return {"code": 0, "message": "success", "data": {"reply": reply}}


# ------------------------------------------------------------------
# 流式发消息（async，核心高并发路由）
# ------------------------------------------------------------------

@router.post("/conversations/{conversation_id}/messages/stream")
async def send_message_stream(
    conversation_id: str,
    body: MessageCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conv = _verify_conversation_owner(db, current_user.id, conversation_id)
    _maybe_update_knowledge_base(db, conv, body.knowledge_base_id)

    return StreamingResponse(
        _stream_generator(body.content, conversation_id, _db_mod.SessionLocal, request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ------------------------------------------------------------------
# 重新生成（async 流式）
# ------------------------------------------------------------------

@router.post("/conversations/{conversation_id}/messages/{message_id}/regenerate")
async def regenerate_message(
    conversation_id: str,
    message_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _verify_conversation_owner(db, current_user.id, conversation_id)

    target_msg = db.query(Message).filter(
        Message.id == message_id, Message.conversation_id == conversation_id, Message.role == "assistant",
    ).first()
    if not target_msg:
        raise HTTPException(status_code=404, detail="消息不存在或非 assistant 消息")

    prev_user_msg = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id, Message.role == "user", Message.created_at < target_msg.created_at)
        .order_by(desc(Message.created_at))
        .first()
    )
    if not prev_user_msg:
        raise HTTPException(status_code=400, detail="找不到对应的用户消息")

    chat_service.delete_messages_from(db, conversation_id, message_id)

    return StreamingResponse(
        _stream_generator(prev_user_msg.content, conversation_id, _db_mod.SessionLocal, request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ------------------------------------------------------------------
# 编辑消息并重新生成（async 流式）
# ------------------------------------------------------------------

@router.put("/conversations/{conversation_id}/messages/{message_id}")
async def edit_message(
    conversation_id: str,
    message_id: str,
    body: MessageCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _verify_conversation_owner(db, current_user.id, conversation_id)

    edited = chat_service.edit_message_content(db, conversation_id, message_id, body.content)
    if not edited:
        raise HTTPException(status_code=404, detail="消息不存在或非用户消息")

    chat_service.delete_messages_from(db, conversation_id, message_id)

    return StreamingResponse(
        _stream_generator(body.content, conversation_id, _db_mod.SessionLocal, request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ------------------------------------------------------------------
# 消息反馈（👍/👎）
# ------------------------------------------------------------------

@router.post("/conversations/{conversation_id}/messages/{message_id}/feedback")
def submit_feedback(
    conversation_id: str,
    message_id: str,
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _verify_conversation_owner(db, current_user.id, conversation_id)

    feedback = body.get("feedback")  # "up" | "down" | null
    if feedback not in ("up", "down", None):
        raise HTTPException(status_code=400, detail="feedback 必须是 up / down / null")

    msg = (
        db.query(Message)
        .filter(Message.id == message_id, Message.conversation_id == conversation_id)
        .first()
    )
    if not msg:
        raise HTTPException(status_code=404, detail="消息不存在")

    msg.feedback = feedback
    db.commit()
    feedback_text = {"up": "👍 赞同", "down": "👎 反对", None: "取消反馈"}.get(feedback, feedback)
    log_action(db, ACTION_MESSAGE_FEEDBACK, user_id=current_user.id, user_email=current_user.email,
               resource_type="conversation", resource_id=conversation_id,
               detail=f"消息反馈: {feedback_text} (message={message_id})")
    return {"ok": True, "feedback": feedback}
