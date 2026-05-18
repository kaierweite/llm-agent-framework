import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from llm_agent.database import Base


class KnowledgeBaseMember(Base):
    """知识库成员关系表：记录哪些用户可以访问某个知识库。"""
    __tablename__ = "knowledge_base_members"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    knowledge_base_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False, index=True,
        comment="知识库 ID",
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
        comment="用户 ID",
    )
    permission: Mapped[str] = mapped_column(
        String(20), nullable=False, default="read",
        comment="权限级别：read=只读，write=可编辑，admin=管理员",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # 关系
    knowledge_base = relationship("KnowledgeBase", back_populates="members")
    user = relationship("User", back_populates="knowledge_base_memberships")

    def __repr__(self):
        return f"<KnowledgeBaseMember kb_id={self.knowledge_base_id} user_id={self.user_id} permission={self.permission}>"
