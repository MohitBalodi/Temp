import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.certificate import Certificate

# The domain owns these; the table only constrains them. Re-exported so callers
# can keep importing them from app.models.
from app.services.verification.engine import (  # noqa: E402  (import order: domain first)
    VerificationMethod,
    VerificationResult,
)

__all__ = ["Verification", "VerificationMethod", "VerificationResult"]


_METHODS = ", ".join(f"'{m.value}'" for m in VerificationMethod)
_RESULTS = ", ".join(f"'{r.value}'" for r in VerificationResult)


class Verification(Base):
    """One verification attempt and the evidence behind its result."""

    __tablename__ = "verifications"
    __table_args__ = (
        CheckConstraint(f"method IN ({_METHODS})", name="ck_verifications_method"),
        CheckConstraint(f"result IN ({_RESULTS})", name="ck_verifications_result"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    verifier_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    method: Mapped[str] = mapped_column(String(16))
    # Null when the lookup found no record; what was looked up is in
    # `extracted_fields`, so an unknown number is still auditable.
    certificate_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("certificates.id", ondelete="RESTRICT"), nullable=True
    )
    result: Mapped[str] = mapped_column(String(16), index=True)
    checks: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, server_default="[]")
    extracted_fields: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    certificate: Mapped[Certificate | None] = relationship(lazy="joined")
