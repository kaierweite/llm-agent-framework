"""
统一文档解析模块 —— 支持 PDF / 文本 / CSV 等格式的文本提取。

依赖：
  pypdf   — PDF 文本提取
  chardet — 文件编码自动检测
"""

from __future__ import annotations

import csv
import io
import os
from typing import Optional

import chardet


# ── 编码检测 ──────────────────────────────────────────────

def detect_encoding(file_path: str, sample_size: int = 64 * 1024) -> str:
    """检测文件编码，返回编码名称（如 'utf-8', 'gbk' 等）。

    对小文件（< sample_size）整体检测；大文件只读前 sample_size 字节。
    如果检测失败或置信度太低，回退到 utf-8。
    """
    try:
        with open(file_path, "rb") as f:
            raw = f.read(sample_size)
        result = chardet.detect(raw)
        encoding = result.get("encoding") or "utf-8"
        confidence = result.get("confidence", 0)
        # 置信度太低时回退
        if confidence < 0.5:
            return "utf-8"
        return encoding
    except Exception:
        return "utf-8"


def read_text_file(file_path: str, encoding: Optional[str] = None, limit: int = 100_000) -> str:
    """读取文本文件，自动检测编码（或使用指定编码），返回文本内容。

    Args:
        file_path: 文件路径
        encoding: 指定编码，None 则自动检测
        limit: 最大读取字符数，防止超大文件 OOM
    """
    if encoding is None:
        encoding = detect_encoding(file_path)

    try:
        with open(file_path, "r", encoding=encoding, errors="replace") as f:
            return f.read(limit)
    except Exception:
        # 最后尝试 utf-8
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                return f.read(limit)
        except Exception:
            return ""


# ── PDF 解析 ──────────────────────────────────────────────

def extract_pdf_text(file_path: str, max_pages: int = 500) -> str:
    """从 PDF 文件提取文本内容。

    使用 pypdf 逐页提取，跳过空白页。
    对扫描版 PDF（无文字层），返回空字符串并由调用方决定后续处理。

    Args:
        file_path: PDF 文件路径
        max_pages: 最多处理页数，防止超大 PDF 卡死
    """
    try:
        from pypdf import PdfReader
    except ImportError:
        return "[pypdf 未安装，无法解析 PDF]"

    try:
        reader = PdfReader(file_path)
    except Exception as e:
        return f"[PDF 解析失败: {e}]"

    pages = reader.pages[:max_pages]
    texts = []

    for i, page in enumerate(pages):
        try:
            text = page.extract_text() or ""
            text = text.strip()
            if text:
                texts.append(f"--- 第 {i + 1} 页 ---\n{text}")
        except Exception:
            continue

    if not texts:
        return "[PDF 无文字内容（可能是扫描版）]"

    return "\n\n".join(texts)


def extract_pdf_metadata(file_path: str) -> dict:
    """提取 PDF 元数据（标题、作者、页数等）。"""
    try:
        from pypdf import PdfReader
        reader = PdfReader(file_path)
        info = reader.metadata or {}
        return {
            "page_count": len(reader.pages),
            "title": getattr(info, "title", None) or "",
            "author": getattr(info, "author", None) or "",
            "subject": getattr(info, "subject", None) or "",
            "creator": getattr(info, "creator", None) or "",
        }
    except Exception:
        return {"page_count": 0, "title": "", "author": "", "subject": "", "creator": ""}


# ── CSV 解析增强 ──────────────────────────────────────────

def extract_csv_text(file_path: str, max_rows: int = 200) -> str:
    """解析 CSV 文件，返回格式化的文本（表头 + 行数据）。

    自动检测编码，处理各种分隔符。
    """
    encoding = detect_encoding(file_path)

    try:
        with open(file_path, "r", encoding=encoding, errors="replace") as f:
            # 先读一小段来检测分隔符
            sample = f.read(4096)
            f.seek(0)

            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
            except csv.Error:
                dialect = csv.excel  # 默认逗号分隔

            reader = csv.reader(f, dialect)
            rows = []
            for i, row in enumerate(reader):
                rows.append(row)
                if i >= max_rows:
                    break

        if not rows:
            return "[空 CSV 文件]"

        headers = rows[0]
        data_rows = rows[1:]

        lines = ["| " + " | ".join(headers) + " |"]
        lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
        for row in data_rows:
            # 补齐列数
            padded = row + [""] * (len(headers) - len(row))
            lines.append("| " + " | ".join(padded[:len(headers)]) + " |")

        result = "\n".join(lines)
        if len(rows) > max_rows:
            result += f"\n\n... (共 {max_rows}+ 行，已截断)"

        return result
    except Exception as e:
        return f"[CSV 解析失败: {e}]"


# ── 统一入口 ──────────────────────────────────────────────

def parse_document(file_path: str) -> dict:
    """统一文档解析入口，根据文件类型返回结构化结果。

    Returns:
        {
            "type": "pdf" | "text" | "csv" | "code" | "unknown",
            "content": str,       # 提取的文本内容
            "metadata": dict,     # 文件元数据
            "encoding": str,      # 检测到的编码
        }
    """
    ext = os.path.splitext(file_path)[1].lower().lstrip(".")

    if ext == "pdf":
        content = extract_pdf_text(file_path)
        metadata = extract_pdf_metadata(file_path)
        return {
            "type": "pdf",
            "content": content,
            "metadata": metadata,
            "encoding": "binary",
        }

    if ext == "csv":
        encoding = detect_encoding(file_path)
        content = extract_csv_text(file_path)
        return {
            "type": "csv",
            "content": content,
            "metadata": {"encoding": encoding},
            "encoding": encoding,
        }

    # 文本类文件（txt / md / json / log / 代码等）
    encoding = detect_encoding(file_path)
    content = read_text_file(file_path, encoding=encoding)
    return {
        "type": "text",
        "content": content,
        "metadata": {"encoding": encoding, "ext": ext},
        "encoding": encoding,
    }
