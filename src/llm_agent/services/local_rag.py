"""
本地 RAG pipeline —— 基于 sentence-transformers + ChromaDB。

提供本地向量检索能力，不依赖 AnythingLLM。
适用于轻量级知识库问答场景。

依赖：
  sentence-transformers — 本地 embedding 模型
  chromadb              — 轻量向量数据库
"""

from __future__ import annotations

import os
import hashlib
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── 全局单例（懒加载，避免重复初始化） ──────────────────

_embedding_model = None
_chroma_client = None


def _get_embedding_model():
    """懒加载 sentence-transformers 模型（首次调用时下载模型）。

    使用 BGE-small-zh-v1.5，中文效果好，体积小（~90MB）。
    """
    global _embedding_model
    if _embedding_model is not None:
        return _embedding_model

    try:
        from sentence_transformers import SentenceTransformer
        model_name = os.environ.get("RAG_EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5")
        logger.info(f"Loading embedding model: {model_name}")
        _embedding_model = SentenceTransformer(model_name)
        logger.info("Embedding model loaded successfully")
        return _embedding_model
    except ImportError:
        logger.warning("sentence-transformers not installed, local RAG unavailable")
        return None
    except Exception as e:
        logger.error(f"Failed to load embedding model: {e}")
        return None


def _get_chroma_client():
    """获取 ChromaDB 持久化客户端。"""
    global _chroma_client
    if _chroma_client is not None:
        return _chroma_client

    try:
        import chromadb
        from chromadb.config import Settings as ChromaSettings

        persist_dir = os.environ.get(
            "RAG_CHROMA_DIR",
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "chroma_data"),
        )
        persist_dir = os.path.abspath(persist_dir)
        os.makedirs(persist_dir, exist_ok=True)

        _chroma_client = chromadb.PersistentClient(
            path=persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        logger.info(f"ChromaDB initialized at: {persist_dir}")
        return _chroma_client
    except ImportError:
        logger.warning("chromadb not installed, local RAG unavailable")
        return None
    except Exception as e:
        logger.error(f"Failed to initialize ChromaDB: {e}")
        return None


# ── 文本分块 ──────────────────────────────────────────────

def chunk_text(
    text: str,
    chunk_size: int = 512,
    chunk_overlap: int = 64,
) -> list[str]:
    """将长文本切分为固定大小的块，带重叠窗口。

    Args:
        text: 原始文本
        chunk_size: 每块最大字符数
        chunk_overlap: 块间重叠字符数
    """
    if not text or not text.strip():
        return []

    text = text.strip()

    # 按段落先分割
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]

    chunks = []
    current_chunk = ""

    for para in paragraphs:
        if len(current_chunk) + len(para) + 1 <= chunk_size:
            current_chunk = f"{current_chunk}\n{para}" if current_chunk else para
        else:
            if current_chunk:
                chunks.append(current_chunk)
            # 如果单个段落超长，强制切分
            if len(para) > chunk_size:
                for i in range(0, len(para), chunk_size - chunk_overlap):
                    chunks.append(para[i : i + chunk_size])
                current_chunk = ""
            else:
                current_chunk = para

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


# ── 核心 API ──────────────────────────────────────────────

def index_document(
    kb_id: str,
    doc_id: str,
    text: str,
    metadata: Optional[dict] = None,
) -> int:
    """将文档文本索引到 ChromaDB。

    Args:
        kb_id: 知识库 ID（作为 collection 名）
        doc_id: 文档 ID
        text: 文档全文
        metadata: 附加元数据

    Returns:
        索引的 chunk 数量
    """
    model = _get_embedding_model()
    client = _get_chroma_client()
    if model is None or client is None:
        logger.warning("Local RAG not available, skipping indexing")
        return 0

    chunks = chunk_text(text)
    if not chunks:
        return 0

    # 生成 chunk IDs（基于内容哈希，支持幂等更新）
    chunk_ids = []
    for i, chunk in enumerate(chunks):
        content_hash = hashlib.md5(chunk.encode()).hexdigest()[:8]
        chunk_ids.append(f"{doc_id}_chunk_{i}_{content_hash}")

    # 生成 embeddings
    embeddings = model.encode(chunks, show_progress_bar=False).tolist()

    # 构建元数据
    metadatas = []
    for i, chunk in enumerate(chunks):
        meta = {
            "doc_id": doc_id,
            "kb_id": kb_id,
            "chunk_index": i,
            "total_chunks": len(chunks),
        }
        if metadata:
            meta.update(metadata)
        metadatas.append(meta)

    # 存入 ChromaDB
    collection_name = f"kb_{kb_id}"
    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    # 先删除该文档的旧 chunks（幂等）
    try:
        existing = collection.get(where={"doc_id": doc_id})
        if existing and existing["ids"]:
            collection.delete(ids=existing["ids"])
    except Exception:
        pass

    # ChromaDB 单次 upsert 有数量限制，分批写入
    batch_size = 100
    for start in range(0, len(chunk_ids), batch_size):
        end = start + batch_size
        collection.upsert(
            ids=chunk_ids[start:end],
            embeddings=embeddings[start:end],
            documents=chunks[start:end],
            metadatas=metadatas[start:end],
        )

    logger.info(f"Indexed {len(chunks)} chunks for doc {doc_id} in kb {kb_id}")
    return len(chunks)


def search(
    kb_id: str,
    query: str,
    top_k: int = 5,
) -> list[dict]:
    """在指定知识库中进行向量检索。

    Args:
        kb_id: 知识库 ID
        query: 查询文本
        top_k: 返回最相关的 chunk 数量

    Returns:
        [{"content": str, "score": float, "doc_id": str, "metadata": dict}, ...]
    """
    model = _get_embedding_model()
    client = _get_chroma_client()
    if model is None or client is None:
        return []

    collection_name = f"kb_{kb_id}"
    try:
        collection = client.get_collection(name=collection_name)
    except Exception:
        return []

    # 查询向量化
    query_embedding = model.encode([query], show_progress_bar=False).tolist()

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    items = []
    if results and results["documents"]:
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            # cosine distance → similarity score
            score = 1.0 - dist
            items.append({
                "content": doc,
                "score": round(score, 4),
                "doc_id": meta.get("doc_id", ""),
                "metadata": meta,
            })

    return items


def delete_document(kb_id: str, doc_id: str) -> bool:
    """删除指定文档的所有 chunks。"""
    client = _get_chroma_client()
    if client is None:
        return False

    collection_name = f"kb_{kb_id}"
    try:
        collection = client.get_collection(name=collection_name)
        existing = collection.get(where={"doc_id": doc_id})
        if existing and existing["ids"]:
            collection.delete(ids=existing["ids"])
            logger.info(f"Deleted {len(existing['ids'])} chunks for doc {doc_id}")
        return True
    except Exception:
        return False


def delete_knowledge_base(kb_id: str) -> bool:
    """删除整个知识库的 collection。"""
    client = _get_chroma_client()
    if client is None:
        return False

    collection_name = f"kb_{kb_id}"
    try:
        client.delete_collection(name=collection_name)
        logger.info(f"Deleted collection for kb {kb_id}")
        return True
    except Exception:
        return False


def is_available() -> bool:
    """检查本地 RAG 是否可用。"""
    return _get_embedding_model() is not None and _get_chroma_client() is not None
