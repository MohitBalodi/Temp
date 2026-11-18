"""Admin read models: the audit trail and headline counts.

Read-only — nothing here writes, so no audit rows of its own.
"""

from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models import (
    AuditLog,
    Certificate,
    CertificateStatus,
    Institution,
    ReviewCase,
    ReviewStatus,
    User,
    Verification,
)
from app.services.verification.engine import VerificationResult

RECENT_DAYS = 7

# A verification request open longer than this is overdue on the dashboard.
# Mirrors `services.reviews.STALE_DAYS`, which is the same promise to the
# verifier; kept as its own constant so this module stays read-only.
STALE_REQUEST_DAYS = 7


def _count(db: Session, stmt: Select[Any]) -> int:
    return db.scalar(select(func.count()).select_from(stmt.subquery())) or 0


def _escape_like(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\%").replace("_", "\_")


def list_audit(
    db: Session,
    *,
    action: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int,
    size: int,
) -> tuple[list[AuditLog], int]:
    """Newest first. `action` matches by prefix, so "certificate." covers every
    certificate action and "auth.login" covers successes only."""
    stmt = select(AuditLog)
    if action and action.strip():
        stmt = stmt.where(AuditLog.action.like(f"{_escape_like(action.strip())}%", escape="\\"))
    if date_from:
        stmt = stmt.where(
            AuditLog.created_at >= datetime.combine(date_from, datetime.min.time(), UTC)
        )
    if date_to:
        # Inclusive of the whole end day.
        stmt = stmt.where(
            AuditLog.created_at
            < datetime.combine(date_to + timedelta(days=1), datetime.min.time(), UTC)
        )

    total = _count(db, stmt)
    items = db.scalars(
        stmt.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    ).all()
    return list(items), total


def stats(db: Session) -> dict[str, Any]:
    since = datetime.now(UTC) - timedelta(days=RECENT_DAYS)

    by_result = {
        result.value: _count(db, select(Verification).where(Verification.result == result.value))
        for result in VerificationResult
    }

    open_requests = select(ReviewCase).where(ReviewCase.status != ReviewStatus.CLOSED.value)
    stale_before = datetime.now(UTC) - timedelta(days=STALE_REQUEST_DAYS)

    return {
        "institutions": _count(db, select(Institution)),
        "institutions_active": _count(
            db, select(Institution).where(Institution.is_active.is_(True))
        ),
        "users": _count(db, select(User)),
        "certificates": _count(db, select(Certificate)),
        "certificates_revoked": _count(
            db, select(Certificate).where(Certificate.status == CertificateStatus.REVOKED.value)
        ),
        "verifications": sum(by_result.values()),
        "verifications_by_result": by_result,
        # Tier 2 item 9. An institution that never answers is the failure mode
        # worth watching, so the overdue count sits beside the open one.
        "requests_open": _count(db, open_requests),
        "requests_open_over_7_days": _count(
            db, open_requests.where(ReviewCase.created_at < stale_before)
        ),
        "last_7_days": {
            "certificates": _count(db, select(Certificate).where(Certificate.created_at >= since)),
            "verifications": _count(
                db, select(Verification).where(Verification.created_at >= since)
            ),
            "logins": _count(
                db,
                select(AuditLog).where(
                    AuditLog.action == "auth.login", AuditLog.created_at >= since
                ),
            ),
            "failed_logins": _count(
                db,
                select(AuditLog).where(
                    AuditLog.action == "auth.login_failed", AuditLog.created_at >= since
                ),
            ),
        },
    }
