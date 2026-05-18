"""
迁移脚本：批量修复已有知识库的 AnythingLLM workspace 聊天设置。

用法：
    cd llm-agent-framework
    python -m scripts.fix_existing_kb_chat_settings

会遍历所有已有知识库，对每个有 anythingllm_workspace_slug 的知识库，
调用 AnythingLLM API 配置聊天模型（使用全局默认配置）。
"""

import sys
import os
import io

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# 修复 Windows 终端编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from llm_agent.config import settings
import llm_agent.database as db_module
from llm_agent.models.knowledge_base import KnowledgeBase
from llm_agent.services import anythingllm_service
from llm_agent.services.anythingllm_service import AnythingLLMError


def main():
    db_module.init_database(settings.database_url)
    db = db_module.SessionLocal()
    try:
        kbs = db.query(KnowledgeBase).filter(
            KnowledgeBase.anythingllm_workspace_slug.isnot(None),
            KnowledgeBase.anythingllm_workspace_slug != "",
        ).all()

        print(f"找到 {len(kbs)} 个知识库需要检查")
        print(f"全局默认配置: provider={settings.anythingllm_chat_provider}, model={settings.anythingllm_chat_model}")
        print()

        success = 0
        failed = 0
        skipped = 0

        for kb in kbs:
            slug = kb.anythingllm_workspace_slug
            print(f"  [{kb.id[:8]}] {kb.name} (slug={slug})")

            try:
                anythingllm_service.update_workspace_chat_settings(
                    slug,
                    chat_provider=settings.anythingllm_chat_provider,
                    chat_model=settings.anythingllm_chat_model,
                )
                print(f"    ✅ 已更新")
                success += 1
            except AnythingLLMError as e:
                print(f"    ❌ 失败: {e.message}")
                failed += 1
            except Exception as e:
                print(f"    ❌ 异常: {e}")
                failed += 1

        print()
        print(f"完成: 成功={success}, 失败={failed}, 跳过={skipped}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
