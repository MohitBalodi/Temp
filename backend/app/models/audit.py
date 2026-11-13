from datetime import datetime
from typing import Any

from sqlalchemy import DDL, BigInteger, DateTime, ForeignKey, String, event, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.user import User


class AuditLog(Base):
    """Append-only. A trigger rejects UPDATE and DELETE (see APPEND_ONLY_DDL)."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(64), index=True)
    entity: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    meta: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    actor: Mapped[User | None] = relationship(lazy="joined")

    @property
    def actor_email(self) -> str | None:
        return self.actor.email if self.actor else None


# Shared by the Alembic migration and by `create_all` (tests), so both get it.
APPEND_ONLY_FUNCTION_SQL = """
CREATE OR REPLACE FUNCTION audit_log_append_only() RETURNS trigger AS $$
BEGIN
    -- Avoid percent signs in this SQL: SQLAlchemy DDL() runs printf-style formatting on it.
    RAISE EXCEPTION USING MESSAGE = 'audit_log is append-only (' || TG_OP || ' not allowed)';
END;
$$ LANGUAGE plpgsql
"""
APPEND_ONLY_TRIGGER_SQL = """
CREATE TRIGGER audit_log_no_update_delete
    BEFORE UPDATE OR DELETE ON audit_log
    FOR EACH ROW EXECUTE FUNCTION audit_log_append_only()
"""

event.listen(AuditLog.__table__, "after_create", DDL(APPEND_ONLY_FUNCTION_SQL))
event.listen(AuditLog.__table__, "after_create", DDL(APPEND_ONLY_TRIGGER_SQL))
