import os
import shutil
import threading
import time
from datetime import datetime
from typing import Optional, Tuple

from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from llm_agent.config import settings
from llm_agent.models.knowledge_base import KnowledgeBase
from llm_agent.models.document import Document
from llm_agent.models.user import User
from llm_agent.models.knowledge_base_member import KnowledgeBaseMember
from llm_agent.services import anythingllm_service
from llm_agent.services.anythingllm_service import AnythingLLMError
from llm_agent.services import document_parser
from llm_agent.services import local_rag


class KnowledgeError(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def _ensure_upload_dir(kb_id: str) -> str:
    path = os.path.join(settings.upload_dir, kb_id)
    os.makedirs(path, exist_ok=True)
    return path


def create_knowledge_base(
    db: Session, owner_id: str, name: str, description: str = "",
    chat_provider: Optional[str] = None,
    chat_model: Optional[str] = None,
) -> KnowledgeBase:
    # 检查同名知识库是否已存在
    existing = (
        db.query(KnowledgeBase)
        .filter(
            KnowledgeBase.owner_id == owner_id,
            KnowledgeBase.name == name,
        )
        .first()
    )
    if existing:
        raise KnowledgeError(409, f"知识库名称「{name}」已存在，请使用其他名称")

    kb = KnowledgeBase(owner_id=owner_id, name=name, description=description)
    db.add(kb)
    db.flush()

    try:
        workspace = anythingllm_service.create_workspace(name, description)
        kb.anythingllm_workspace_slug = workspace.get("slug", "")
    except AnythingLLMError as e:
        db.rollback()
        raise KnowledgeError(e.code, f"Failed to create AnythingLLM workspace: {e.message}") from e

    # 配置 workspace 聊天设置：优先用前端传入的值，否则用全局默认配置
    _chat_provider = chat_provider or settings.anythingllm_chat_provider
    _chat_model = chat_model or settings.anythingllm_chat_model
    try:
        anythingllm_service.update_workspace_chat_settings(
            kb.anythingllm_workspace_slug,
            chat_provider=_chat_provider,
            chat_model=_chat_model,
        )
    except AnythingLLMError:
        pass  # 配置失败不影响知识库创建

    _ensure_upload_dir(kb.id)
    db.commit()
    db.refresh(kb)
    return kb


def list_knowledge_bases(
    db: Session, owner_id: str, page: int = 1, page_size: int = 20
) -> Tuple[list, int]:
    # ── 1. 自有知识库 ──
    own_total = (
        db.query(func.count(KnowledgeBase.id))
        .filter(KnowledgeBase.owner_id == owner_id)
        .scalar()
    )

    own_rows = (
        db.query(
            KnowledgeBase,
            func.count(Document.id).label("document_count"),
        )
        .outerjoin(Document, Document.knowledge_base_id == KnowledgeBase.id)
        .filter(KnowledgeBase.owner_id == owner_id)
        .group_by(KnowledgeBase.id)
        .order_by(desc(KnowledgeBase.updated_at))
        .all()
    )

    items = []
    seen_ids = set()
    for kb, doc_count in own_rows:
        seen_ids.add(kb.id)
        items.append({
            "id": kb.id,
            "name": kb.name,
            "description": kb.description,
            "document_count": doc_count,
            "is_active": kb.is_active,
            "is_shared": False,
            "shared_by": None,
            "permission": "owner",
            "created_at": kb.created_at,
            "updated_at": kb.updated_at,
        })

    # ── 2. 共享知识库（通过活跃分享码可访问的） ──
    from llm_agent.models.knowledge_base_share import KnowledgeBaseShare
    from llm_agent.models.user import User as UserModel

    now_utc = datetime.utcnow()

    shared_rows = (
        db.query(
            KnowledgeBase,
            KnowledgeBaseShare.shared_by_id,
            KnowledgeBaseShare.permission,
            UserModel.display_name,
            func.count(Document.id).label("document_count"),
        )
        .join(KnowledgeBaseShare, KnowledgeBaseShare.knowledge_base_id == KnowledgeBase.id)
        .outerjoin(UserModel, UserModel.id == KnowledgeBaseShare.shared_by_id)
        .outerjoin(Document, Document.knowledge_base_id == KnowledgeBase.id)
        .filter(
            KnowledgeBase.owner_id != owner_id,
            KnowledgeBaseShare.is_active == True,
            KnowledgeBaseShare.expires_at > now_utc,
        )
        .group_by(KnowledgeBase.id, KnowledgeBaseShare.shared_by_id, KnowledgeBaseShare.permission, UserModel.display_name)
        .order_by(desc(KnowledgeBase.updated_at))
        .all()
    )

    for kb, shared_by_id, share_perm, shared_by_name, doc_count in shared_rows:
        if kb.id in seen_ids:
            continue
        seen_ids.add(kb.id)
        items.append({
            "id": kb.id,
            "name": kb.name,
            "description": kb.description,
            "document_count": doc_count,
            "is_active": kb.is_active,
            "is_shared": True,
            "shared_by": shared_by_name or shared_by_id,
            "permission": share_perm,
            "created_at": kb.created_at,
            "updated_at": kb.updated_at,
        })

    total = len(items)

    # ── 3. 分页（合并后整体分页） ──
    start = (page - 1) * page_size
    items = items[start : start + page_size]

    return items, total


def get_knowledge_base(
    db: Session, owner_id: str, kb_id: str
) -> Optional[KnowledgeBase]:
    return (
        db.query(KnowledgeBase)
        .filter(
            KnowledgeBase.id == kb_id,
            KnowledgeBase.owner_id == owner_id,
        )
        .first()
    )


def get_knowledge_base_by_id(
    db: Session, kb_id: str
) -> Optional[KnowledgeBase]:
    """按 ID 查询知识库，不限 owner。用于共享知识库访问。"""
    return db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()


def delete_knowledge_base(db: Session, owner_id: str, kb_id: str) -> bool:
    kb = get_knowledge_base(db, owner_id, kb_id)
    if not kb:
        return False

    if kb.anythingllm_workspace_slug:
        try:
            anythingllm_service.delete_workspace(kb.anythingllm_workspace_slug)
        except AnythingLLMError as e:
            print(f"Warning: failed to delete AnythingLLM workspace: {e.message}")

    # 清理本地 RAG 索引
    try:
        local_rag.delete_knowledge_base(kb_id)
    except Exception as e:
        print(f"Warning: failed to delete local RAG collection for kb {kb_id}: {e}")

    for doc in kb.documents:
        if doc.file_path and os.path.exists(doc.file_path):
            try:
                os.remove(doc.file_path)
            except OSError as e:
                print(f"Warning: failed to delete file {doc.file_path}: {e}")

    kb_dir = os.path.join(settings.upload_dir, kb_id)
    if os.path.isdir(kb_dir):
        try:
            shutil.rmtree(kb_dir)
        except OSError as e:
            print(f"Warning: failed to delete directory {kb_dir}: {e}")

    db.delete(kb)
    db.commit()
    return True


def rename_knowledge_base(
    db: Session,
    owner_id: str,
    kb_id: str,
    new_name: str,
    new_description: Optional[str] = None,
) -> KnowledgeBase:
    kb = get_knowledge_base(db, owner_id, kb_id)
    if not kb:
        raise KnowledgeError(40401, "Knowledge base not found")

    kb.name = new_name
    if new_description is not None:
        kb.description = new_description
    db.commit()
    db.refresh(kb)
    return kb


def _embed_document_background(doc_id: str, kb_id: str, save_path: str, workspace_slug: str):
    """后台线程：上传文件到 AnythingLLM 并触发 embedding 向量化，同时索引到本地 RAG。"""
    from llm_agent.database import SessionLocal
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            return

        doc.upload_status = "embedding"
        db.commit()

        # ── 1. 本地 RAG 索引（不依赖 AnythingLLM，始终尝试） ──
        try:
            parsed = document_parser.parse_document(save_path)
            if parsed["content"] and not parsed["content"].startswith("["):
                local_rag.index_document(
                    kb_id=kb_id,
                    doc_id=doc_id,
                    text=parsed["content"],
                    metadata={"filename": doc.filename, "file_type": doc.file_type},
                )
        except Exception as e:
            print(f"Warning: local RAG indexing failed for doc {doc_id}: {e}")

        # ── 2. AnythingLLM 上传 + embedding ──
        upload_result = anythingllm_service.upload_document(workspace_slug, save_path)
        doc_location = upload_result.get("documents", [{}])[0].get(
            "location", upload_result.get("location", "")
        )
        if not doc_location and isinstance(upload_result.get("documents"), list):
            for d in upload_result["documents"]:
                if "location" in d:
                    doc_location = d["location"]
                    break

        # AnythingLLM 上传 API 可能返回绝对路径（如 C:\...\custom-documents\xxx.json），
        # 但 update-embeddings API 需要相对路径（如 custom-documents/xxx.json）
        if doc_location and ("custom-documents\\" in doc_location or "custom-documents/" in doc_location):
            idx = doc_location.lower().find("custom-documents")
            doc_location = doc_location[idx:]

        anythingllm_service.move_document_to_workspace(workspace_slug, doc_location)

        doc.anythingllm_doc_id = doc_location
        doc.upload_status = "ready"
        db.commit()
    except Exception as e:
        try:
            doc = db.query(Document).filter(Document.id == doc_id).first()
            if doc:
                doc.upload_status = "failed"
                doc.error_message = str(e)[:1000]
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


def upload_document(db: Session, owner_id: str, kb_id: str, file) -> Document:
    """上传文档：立即保存文件并返回，AnythingLLM 上传+embedding 在后台执行。"""
    kb = get_knowledge_base(db, owner_id, kb_id)
    if not kb:
        raise KnowledgeError(40401, "Knowledge base not found")

    file_size = 0
    content = file.file.read()
    file_size = len(content)
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if file_size > max_bytes:
        raise KnowledgeError(
            41301,
            f"File too large: {file_size} bytes exceeds limit of {settings.max_upload_size_mb}MB",
        )

    original_filename = file.filename or "unnamed"
    save_dir = _ensure_upload_dir(kb_id)
    save_path = os.path.join(save_dir, original_filename)
    if os.path.exists(save_path):
        name, ext = os.path.splitext(original_filename)
        save_path = os.path.join(save_dir, f"{name}_{int(time.time())}{ext}")

    with open(save_path, "wb") as f:
        f.write(content)

    file_type = None
    if "." in os.path.basename(save_path):
        file_type = os.path.basename(save_path).rsplit(".", 1)[-1].lower()

    doc = Document(
        knowledge_base_id=kb_id,
        filename=os.path.basename(save_path),
        file_path=save_path,
        file_size=file_size,
        file_type=file_type,
        upload_status="uploading",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # 后台线程处理 AnythingLLM 上传 + embedding
    thread = threading.Thread(
        target=_embed_document_background,
        args=(doc.id, kb_id, save_path, kb.anythingllm_workspace_slug),
        daemon=True,
    )
    thread.start()

    return doc


def list_documents(
    db: Session, owner_id: str, kb_id: str, page: int = 1, page_size: int = 20
) -> Tuple[list, int]:
    kb = get_knowledge_base(db, owner_id, kb_id)
    if not kb:
        raise KnowledgeError(40401, "Knowledge base not found")

    total = (
        db.query(func.count(Document.id))
        .filter(Document.knowledge_base_id == kb_id)
        .scalar()
    )

    rows = (
        db.query(Document)
        .filter(Document.knowledge_base_id == kb_id)
        .order_by(desc(Document.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = []
    for doc in rows:
        items.append({
            "id": doc.id,
            "filename": doc.filename,
            "file_size": doc.file_size,
            "file_type": doc.file_type,
            "upload_status": doc.upload_status,
            "error_message": doc.error_message,
            "created_at": doc.created_at,
            "updated_at": doc.updated_at,
        })

    return items, total


def delete_document(db: Session, owner_id: str, doc_id: str) -> bool:
    doc = (
        db.query(Document)
        .filter(Document.id == doc_id)
        .first()
    )
    if not doc:
        return False

    kb = get_knowledge_base(db, owner_id, doc.knowledge_base_id)
    if not kb:
        return False

    if doc.anythingllm_doc_id:
        try:
            anythingllm_service.delete_document(doc.anythingllm_doc_id)
        except AnythingLLMError as e:
            print(f"Warning: failed to delete AnythingLLM document: {e.message}")

    # 清理本地 RAG 索引
    try:
        local_rag.delete_document(doc.knowledge_base_id, doc_id)
    except Exception as e:
        print(f"Warning: failed to delete local RAG index for doc {doc_id}: {e}")

    if doc.file_path and os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except OSError as e:
            print(f"Warning: failed to delete file {doc.file_path}: {e}")

    db.delete(doc)
    db.commit()
    return True


def query_knowledge_base(
    db: Session, owner_id: str, kb_id: str, question: str
) -> str:
    kb = get_knowledge_base(db, owner_id, kb_id)
    if not kb:
        # 回退：可能是共享知识库，owner_id 不匹配但用户有访问权
        kb = get_knowledge_base_by_id(db, kb_id)
    if not kb:
        raise KnowledgeError(40401, "Knowledge base not found")

    if not kb.anythingllm_workspace_slug:
        raise KnowledgeError(40001, "Knowledge base has no AnythingLLM workspace")

    try:
        answer = anythingllm_service.query_workspace(
            kb.anythingllm_workspace_slug, question
        )
        return answer
    except AnythingLLMError as e:
        raise KnowledgeError(e.code, f"Query failed: {e.message}") from e


# ── 预览相关辅助 ──────────────────────────────────────────────

_CODE_EXTENSIONS = {"py", "js", "ts", "jsx", "tsx", "html", "xml", "yaml", "yml", "json", "log", "css", "scss", "java", "c", "cpp", "h", "go", "rs", "rb", "php", "sh", "bat", "sql"}

_EXT_TO_LANG = {
    "py": "python", "js": "javascript", "ts": "typescript",
    "jsx": "jsx", "tsx": "tsx", "html": "html", "xml": "xml",
    "yaml": "yaml", "yml": "yaml", "json": "json", "log": "text",
    "css": "css", "scss": "scss", "java": "java", "c": "c",
    "cpp": "cpp", "h": "c", "go": "go", "rs": "rust",
    "rb": "ruby", "php": "php", "sh": "bash", "bat": "batch",
    "sql": "sql", "md": "markdown",
}


def _truncate(content: str, limit: int = 10000) -> str:
    if len(content) > limit:
        return content[:limit] + "\n\n...（内容已截断）"
    return content


def _truncate_list(items: list, limit: int) -> list:
    return items[:limit] if len(items) > limit else items


def preview_document(db: Session, owner_id: str, doc_id: str) -> Optional[dict]:
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        return None

    kb = get_knowledge_base(db, owner_id, doc.knowledge_base_id)
    if not kb:
        return None

    if not doc.file_path or not os.path.exists(doc.file_path):
        return None

    ext = (doc.file_type or "").lower()

    # ── Markdown → 渲染为 HTML ──
    if ext == "md":
        try:
            import markdown as md_lib
            with open(doc.file_path, "r", encoding="utf-8", errors="replace") as f:
                raw = f.read()
            html = md_lib.markdown(
                _truncate(raw),
                extensions=["fenced_code", "tables", "codehilite", "toc"],
            )
            return {"type": "markdown", "content": html, "raw": _truncate(raw)}
        except ImportError:
            with open(doc.file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            return {"type": "text", "content": _truncate(content)}
        except Exception:
            return {"type": "text", "content": "[无法读取文件内容]"}

    # ── CSV → 表格 ──
    if ext == "csv":
        try:
            import csv
            with open(doc.file_path, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.reader(f)
                rows_raw = []
                for i, row in enumerate(reader):
                    rows_raw.append(row)
                    if i >= 200:
                        break
            if not rows_raw:
                return {"type": "text", "content": "[空文件]"}
            headers = rows_raw[0]
            rows = rows_raw[1:]
            return {"type": "table", "sheets": [{"name": "Sheet1", "headers": headers, "rows": rows}]}
        except Exception:
            return {"type": "text", "content": "[无法读取 CSV 文件]"}

        # ── 代码 / 文本文件 ──
    if ext in _CODE_EXTENSIONS:
        try:
            encoding = document_parser.detect_encoding(doc.file_path)
            with open(doc.file_path, "r", encoding=encoding, errors="replace") as f:
                content = f.read()
            lang = _EXT_TO_LANG.get(ext, "text")
            return {"type": "code", "language": lang, "content": _truncate(content)}
        except Exception:
            return {"type": "text", "content": "[无法读取文件内容]"}

        # ── PDF → 文本提取 + 元数据 ──
    if ext == "pdf":
        try:
            text_content = document_parser.extract_pdf_text(doc.file_path)
            metadata = document_parser.extract_pdf_metadata(doc.file_path)
            if text_content and not text_content.startswith("["):
                return {
                    "type": "pdf",
                    "content": _truncate(text_content),
                    "metadata": metadata,
                    "file_url": f"/api/knowledge/documents/{doc_id}/raw",
                }
            # 扫描版 PDF 无文字，回退到 iframe
            return {"type": "pdf", "file_url": f"/api/knowledge/documents/{doc_id}/raw"}
        except Exception:
            return {"type": "pdf", "file_url": f"/api/knowledge/documents/{doc_id}/raw"}

    # ── DOCX → 结构化段落 ──
    if ext == "docx":
        try:
            from docx import Document as DocxDocument
            d = DocxDocument(doc.file_path)
            paragraphs = []
            for p in d.paragraphs:
                text = p.text.strip()
                if text:
                    style_name = (p.style.name or "").lower()
                    if "heading 1" in style_name or "标题 1" in style_name:
                        paragraphs.append({"text": text, "level": 1})
                    elif "heading 2" in style_name or "标题 2" in style_name:
                        paragraphs.append({"text": text, "level": 2})
                    elif "heading 3" in style_name or "标题 3" in style_name:
                        paragraphs.append({"text": text, "level": 3})
                    else:
                        paragraphs.append({"text": text, "level": 0})
            return {"type": "docx", "paragraphs": _truncate_list(paragraphs, 500)}
        except Exception:
            return {"type": "text", "content": "[无法读取 docx 文件内容]"}

    # ── XLSX / XLS → 表格 ──
    if ext in ("xlsx", "xls"):
        try:
            from openpyxl import load_workbook
            wb = load_workbook(doc.file_path, read_only=True, data_only=True)
            sheets = []
            for sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
                rows_raw = []
                row_count = 0
                for row in ws.iter_rows(values_only=True):
                    cells = [str(c) if c is not None else "" for c in row]
                    if any(cells):
                        rows_raw.append(cells)
                    row_count += 1
                    if row_count >= 200:
                        break
                if rows_raw:
                    sheets.append({
                        "name": sheet_name,
                        "headers": rows_raw[0],
                        "rows": rows_raw[1:],
                    })
            wb.close()
            if not sheets:
                return {"type": "text", "content": "[空工作簿]"}
            return {"type": "table", "sheets": sheets}
        except Exception:
            return {"type": "text", "content": "[无法读取 Excel 文件内容]"}

    # ── PPTX → 幻灯片 ──
    if ext == "pptx":
        try:
            from pptx import Presentation
            prs = Presentation(doc.file_path)
            slides = []
            for i, slide in enumerate(prs.slides, 1):
                slide_data = {"page": i, "texts": []}
                for shape in slide.shapes:
                    if shape.has_text_frame:
                        for para in shape.text_frame.paragraphs:
                            text = para.text.strip()
                            if text:
                                slide_data["texts"].append(text)
                if slide_data["texts"]:
                    slides.append(slide_data)
            return {"type": "slides", "slides": _truncate_list(slides, 200)}
        except Exception:
            return {"type": "text", "content": "[无法读取 PPT 文件内容]"}

    # ── .doc → 不支持 ──
    if ext == "doc":
        return {"type": "unsupported", "message": ".doc 格式暂不支持预览，请下载后查看"}

        # ── 其他 → 尝试当文本读（自动检测编码） ──
    try:
        encoding = document_parser.detect_encoding(doc.file_path)
        with open(doc.file_path, "r", encoding=encoding, errors="replace") as f:
            content = f.read()
        return {"type": "text", "content": _truncate(content)}
    except Exception:
        return {"type": "text", "content": "[无法读取文件内容]"}


def get_document_raw(db: Session, owner_id: str, doc_id: str) -> Optional[Document]:
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        return None

    kb = get_knowledge_base(db, owner_id, doc.knowledge_base_id)
    if not kb:
        kb = get_knowledge_base_by_id(db, doc.knowledge_base_id)
    if not kb:
        return None

    if not doc.file_path or not os.path.exists(doc.file_path):
        return None

    return doc


# ==================== 知识库成员管理 ====================

def list_members(
    db: Session, kb_id: str, owner_id: str
) -> list[dict]:
    """列出知识库的所有成员。"""
    kb = get_knowledge_base(db, owner_id, kb_id)
    if not kb:
        raise KnowledgeError(40401, "知识库不存在或无权操作")

    rows = (
        db.query(KnowledgeBaseMember, User)
        .join(User, User.id == KnowledgeBaseMember.user_id)
        .filter(KnowledgeBaseMember.knowledge_base_id == kb_id)
        .order_by(KnowledgeBaseMember.created_at)
        .all()
    )

    return [
        {
            "id": m.id,
            "user_id": m.user_id,
            "email": u.email,
            "display_name": u.display_name,
            "permission": m.permission,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m, u in rows
    ]


def add_member(
    db: Session, kb_id: str, owner_id: str, user_id: str | None, email: str | None, permission: str = "read"
) -> dict:
    """添加知识库成员。
    
    支持两种方式：
    1. 通过 user_id 添加（用户必须存在）
    2. 通过 email 添加（如果用户存在则关联，不存在则创建新成员记录）
    """
    kb = get_knowledge_base(db, owner_id, kb_id)
    if not kb:
        raise KnowledgeError(40401, "知识库不存在或无权操作")

    # 不能添加 owner 自己为成员
    if kb.owner_id == user_id:
        raise KnowledgeError(40001, "不能添加知识库所有者为成员")

    # 如果提供了 user_id，直接使用
    user = None
    if user_id:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise KnowledgeError(40402, "用户不存在")
    elif email:
        # 通过邮箱查找用户
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise KnowledgeError(40402, f"用户不存在：{email}")
        user_id = user.id
    else:
        raise KnowledgeError(40002, "必须提供 user_id 或 email")

    # 检查是否已是成员
    existing = db.query(KnowledgeBaseMember).filter(
        KnowledgeBaseMember.knowledge_base_id == kb_id,
        KnowledgeBaseMember.user_id == user_id,
    ).first()
    if existing:
        raise KnowledgeError(40003, "该用户已是成员")

    member = KnowledgeBaseMember(
        knowledge_base_id=kb_id,
        user_id=user_id,
        permission=permission,
    )
    db.add(member)
    db.commit()
    db.refresh(member)

    return {
        "id": member.id,
        "user_id": member.user_id,
        "email": user.email,
        "display_name": user.display_name,
        "permission": member.permission,
        "created_at": member.created_at.isoformat() if member.created_at else None,
    }


def remove_member(
    db: Session, kb_id: str, owner_id: str, user_id: str
) -> bool:
    """移除知识库成员。"""
    kb = get_knowledge_base(db, owner_id, kb_id)
    if not kb:
        raise KnowledgeError(40401, "知识库不存在或无权操作")

    member = db.query(KnowledgeBaseMember).filter(
        KnowledgeBaseMember.knowledge_base_id == kb_id,
        KnowledgeBaseMember.user_id == user_id,
    ).first()
    if not member:
        raise KnowledgeError(40402, "该用户不是成员")

    db.delete(member)
    db.commit()
    return True


def update_member_permission(
    db: Session, kb_id: str, owner_id: str, user_id: str, permission: str
) -> dict:
    """更新成员权限。"""
    kb = get_knowledge_base(db, owner_id, kb_id)
    if not kb:
        raise KnowledgeError(40401, "知识库不存在或无权操作")

    member = db.query(KnowledgeBaseMember).filter(
        KnowledgeBaseMember.knowledge_base_id == kb_id,
        KnowledgeBaseMember.user_id == user_id,
    ).first()
    if not member:
        raise KnowledgeError(40402, "该用户不是成员")

    member.permission = permission
    db.commit()
    db.refresh(member)

    user = db.query(User).filter(User.id == user_id).first()
    return {
        "id": member.id,
        "user_id": member.user_id,
        "email": user.email,
        "display_name": user.display_name,
        "permission": member.permission,
        "created_at": member.created_at.isoformat() if member.created_at else None,
    }
