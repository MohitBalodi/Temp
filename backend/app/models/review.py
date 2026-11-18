"""Verification requests: a verifier asking an institution to confirm a document.

One case per request, plus a message thread. The case never edits the
verification it came from — a verification is a record of what the system
concluded at a point in time, and an institution's answer is a *later,
separate* fact shown alongside it.
"""

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.institution import Institution
from app.models.user import User
from app.models.verification import Verification

__all__ = ["ReviewCase", "ReviewDecision", "ReviewMessage", "ReviewStatus"]


class ReviewStatus(StrEnum):
    """pending -> needs_info <-> pending -> closed. `closed` is terminal: an
    institution's answer is a matter of record, so a new question about the
    same document is a new request rather than a reopened one."""

    PENDING = "pending"
    NEEDS_INFO = "needs_info"
    CLOSED = "closed"


class ReviewDecision(StrEnum):
    """How a case was closed. Never "fake" or "forged": `NOT_ISSUED` is the
    institution stating it has no such record, which is a fact about the
    registry, not an accusation about the holder."""

    CONFIRMED = "confirmed"
    CONFIRMED_ADDED = "confirmed_added"
    NOT_ISSUED = "not_issued"


_STATUSES = ", ".join(f"'{s.value}'" for s in ReviewStatus)
_DECISIONS = ", ".join(f"'{d.value}'" for d in ReviewDecision)


class ReviewCase(Base):
    """One request for an institution to confirm one verification."""

    __tablename__ = "review_cases"
    __table_args__ = (
        CheckConstraint(f"status IN ({_STATUSES})", name="ck_review_cases_status"),
        CheckConstraint(
            f"decision IS NULL OR decision IN ({_DECISIONS})", name="ck_review_cases_decision"
        ),
        # A decision and a closed status arrive together or not at all.
        CheckConstraint(
            "(status = 'closed') = (decision IS NOT NULL)",
            name="ck_review_cases_decided_when_closed",
        ),
        # At most one *open* case per verification. A closed one does not block
        # a fresh request about the same document.
        Index(
            "uq_review_cases_open_per_verification",
            "verification_id",
            unique=True,
            postgresql_where=text(f"status <> '{ReviewStatus.CLOSED.value}'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    verification_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("verifications.id", ondelete="RESTRICT"), index=True
    )
    # Who is being asked. Taken from the identified record when there is one,
    # otherwise chosen by the verifier.
    institution_id: Mapped[int] = mapped_column(
        ForeignKey("institutions.id", ondelete="RESTRICT"), index=True
    )
    requested_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    status: Mapped[str] = mapped_column(
        String(16), default=ReviewStatus.PENDING.value, server_default=ReviewStatus.PENDING.value
    )
    # The verifier's opening note. Kept on the case rather than as the first
    # message: it is why the request exists, and it is never replied to.
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    decision: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # Required for `not_issued`, optional otherwise: an institution denying a
    # record has to say on what basis.
    decision_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    # Touched by every message and by the decision, so a list can be ordered
    # and shown by "last update" without reading the whole thread.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    verification: Mapped[Verification] = relationship(lazy="joined", back_populates="cases")
    institution: Mapped[Institution] = relationship(lazy="joined")
    requester: Mapped[User] = relationship(lazy="joined", foreign_keys=[requested_by])
    decider: Mapped[User | None] = relationship(lazy="joined", foreign_keys=[decided_by])
    messages: Mapped[list["ReviewMessage"]] = relationship(
        back_populates="case",
        order_by="ReviewMessage.created_at",
        cascade="all, delete-orphan",
    )

    @property
    def is_open(self) -> bool:
        return self.status != ReviewStatus.CLOSED.value


class ReviewMessage(Base):
    """One message in a case's thread, from either side."""

    __tablename__ = "review_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("review_cases.id", ondelete="CASCADE"), index=True
    )
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    case: Mapped[ReviewCase] = relationship(back_populates="messages")
    author: Mapped[User] = relationship(lazy="joined")
