import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, DateTime, Float, func
from sqlalchemy.orm import Mapped, mapped_column

from llm_agent.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    trace_id: Mapped[str | None] = mapped_column(
        String(12), nullable=True, index=True, comment="请求追踪 ID"
    )
    user_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, index=True
    )
    user_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    action: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )
    severity: Mapped[str] = mapped_column(
        String(10), nullable=False, server_default="INFO",
        comment="日志级别: INFO/WARN/ERROR"
    )
    resource_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(100), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="客户端 User-Agent"
    )
    duration_ms: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="请求耗时（毫秒）"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self):
        return f"<AuditLog {self.action} by={self.user_email} severity={self.severity}>"
