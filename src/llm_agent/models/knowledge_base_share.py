import secrets
import string
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import String, DateTime, Boolean, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from llm_agent.database import Base

# 分享码固定有效期：3 天
SHARE_CODE_TTL_DAYS = 3


def _generate_share_code(length: int = 8) -> str:
    """生成短分享码，由大写字母 + 数字组成，易读易输入。"""
    alphabet = string.ascii_uppercase + string.digits
    # 去掉容易混淆的字符 O/0/I/1
    alphabet = alphabet.replace("O", "").replace("0", "").replace("I", "").replace("1", "")
    return "".join(secrets.choice(alphabet) for _ in range(length))


class KnowledgeBaseShare(Base):
    """知识库分享码：owner 生成分享码，持有码的人可访问。"""
    __tablename__ = "knowledge_base_shares"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    knowledge_base_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    shared_by_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    share_code: Mapped[str] = mapped_column(
        String(8), unique=True, nullable=False, index=True,
        default=_generate_share_code,
        comment="分享码，8位大写字母+数字",
    )
    permission: Mapped[str] = mapped_column(
        String(20), nullable=False, default="read",
                comment="权限级别: read=只读, query=可查询",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True,
        comment="是否有效，false=已吊销",
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        comment="过期时间，生成时设为 now + 3天",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    knowledge_base = relationship("KnowledgeBase", backref="shares")
    shared_by = relationship("User", foreign_keys=[shared_by_id])

    __table_args__ = (
        UniqueConstraint(
            "knowledge_base_id", "share_code",
            name="uq_kb_share_code",
        ),
    )

    def __repr__(self):
        return (
            f"<KnowledgeBaseShare kb={self.knowledge_base_id[:8]} "
            f"code={self.share_code} perm={self.permission} active={self.is_active}>"
        )
