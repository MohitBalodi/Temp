from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AuditOut(BaseModel):
    """One audit row. `meta` never holds personal data — identifiers, counts
    and, for a failed login, the email's domain only."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    actor_id: int | None
    actor_email: str | None = None
    action: str
    entity: str
    entity_id: str | None
    meta: dict[str, Any]
    created_at: datetime


class ResultCounts(BaseModel):
    VERIFIED: int = 0
    MISMATCH: int = 0
    REVOKED: int = 0
    MANUAL_REVIEW: int = 0


class RecentCounts(BaseModel):
    certificates: int = 0
    verifications: int = 0
    logins: int = 0
    failed_logins: int = 0


class AdminStats(BaseModel):
    institutions: int
    users: int
    certificates: int
    certificates_revoked: int
    verifications: int
    verifications_by_result: ResultCounts
    last_7_days: RecentCounts = Field(description="Rolling window, not calendar weeks.")
