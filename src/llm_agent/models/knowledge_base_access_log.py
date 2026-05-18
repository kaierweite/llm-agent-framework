import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from llm_agent.database import Base


class KnowledgeBaseAccessLog(Base):
    """知识库访问日志：记录谁在什么时间访问了哪个知识库，做了什么。"""
    __tablename__ = "knowledge_base_access_logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    knowledge_base_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    action: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="访问动作: view=查看详情, query=查询问答, download=下载文档, share=分享",
    )
    detail: Mapped[str | None] = mapped_column(String(500), nullable=True)
    share_code: Mapped[str | None] = mapped_column(
        String(8), nullable=True, index=True,
        comment="通过哪个分享码进入，空表示 owner 直接访问",
    )
    ip_address: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self):
        return (
            f"<KBAccessLog kb={self.knowledge_base_id[:8]} "
            f"user={self.user_id[:8]} action={self.action}>"
        )
