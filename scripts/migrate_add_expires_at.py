"""
迁移脚本：为 knowledge_base_shares 表添加 expires_at 字段。

用法：
    python scripts/migrate_add_expires_at.py

说明：
    - 如果表不存在（全新部署），create_all 会自动创建包含 expires_at 的完整表结构，无需运行此脚本。
    - 如果表已存在但缺少 expires_at 列，运行此脚本添加列并回填 3 天后的过期时间。
    - 幂等：如果 expires_at 列已存在，脚本会跳过。
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from datetime import datetime, timedelta, timezone
from sqlalchemy import text, inspect
from llm_agent.database import engine, init_database
from llm_agent.config import settings


def migrate():
    init_database(settings.database_url)

    with engine.connect() as conn:
        inspector = inspect(engine)

        # 检查表是否存在
        tables = inspector.get_table_names()
        if "knowledge_base_shares" not in tables:
            print("[skip] knowledge_base_shares 表不存在，create_all 会自动创建完整结构")
            return

        # 检查列是否存在
        columns = {col["name"] for col in inspector.get_columns("knowledge_base_shares")}
        if "expires_at" in columns:
            print("[skip] expires_at 列已存在")
            return

        # 添加列
        print("[migrate] 添加 expires_at 列...")
        conn.execute(text(
            "ALTER TABLE knowledge_base_shares "
            "ADD COLUMN expires_at DATETIME NOT NULL "
            "DEFAULT '2026-05-13 00:00:00'"
        ))

        # 回填已有记录：created_at + 3天
        print("[migrate] 回填已有记录的 expires_at...")
        conn.execute(text(
            "UPDATE knowledge_base_shares "
            "SET expires_at = DATE_ADD(created_at, INTERVAL 3 DAY) "
            "WHERE expires_at = '2026-05-13 00:00:00'"
        ))

        conn.commit()
        print("[done] 迁移完成")


if __name__ == "__main__":
    migrate()
