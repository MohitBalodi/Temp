"""Verification requests: a verifier asks an institution to confirm a document.

What this is for: the system reaches MANUAL_REVIEW when it has no evidence
either way — an unknown number, an unreadable page, a layout it does not know —
and MISMATCH when what it read disagrees with the registry. Neither is a
verdict on the document, and only the issuing institution can settle it. This
module is that conversation, recorded.

Rules worth knowing before reading the code:

* The verification is never edited. A case points at it; the institution's
  answer is a later, separate fact shown beside the original result.
* An institution only ever sees cases addressed to it; a verifier only their
  own; an admin reads everything and decides nothing.
* `closed` is terminal. A further question about the same document is a new
  request, so the record of what was answered when stays intact.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import (
    Certificate,
    Institution,
    ReviewCase,
    ReviewDecision,
    ReviewMessage,
    ReviewStatus,
    Role,
    User,
    Verification,
    VerificationResult,
)
from app.schemas.certificates import CertificateFields
from app.services import audit, certificates

# Only a result the system could not settle may be escalated. A VERIFIED or
# REVOKED verification has an answer already, and asking an institution to
# re-confirm cryptography would teach verifiers to distrust it.
ESCALATABLE_RESULTS = frozenset(
    {VerificationResult.MANUAL_REVIEW.value, VerificationResult.MISMATCH.value}
)

# "Open for too long" on the admin dashboard.
STALE_DAYS = 7


# --- lookups ------------------------------------------------------------------


def _case_or_404(db: Session, case_id: uuid.UUID) -> ReviewCase:
    case = db.get(ReviewCase, case_id)
    if case is None:
        raise AppError(404, "not_found", "Verification request not found.")
    return case


def _visible(case: ReviewCase, user: User) -> bool:
    """Who may see a case at all.

    An institution user sees what was addressed to their institution; the
    verifier who asked sees their own; an admin sees everything. Anyone else
    gets the same answer as for a case that does not exist.
    """
    if user.role == Role.ADMIN:
        return True
    if user.role == Role.INSTITUTION:
        return case.institution_id == user.institution_id
    return case.requested_by == user.id


def get_case(db: Session, user: User, case_id: uuid.UUID) -> ReviewCase:
    case = _case_or_404(db, case_id)
    if not _visible(case, user):
        # 404, not 403: whether a case exists is itself information.
        raise AppError(404, "not_found", "Verification request not found.")
    return case


def _scope(stmt: Select[tuple[ReviewCase]], user: User) -> Select[tuple[ReviewCase]]:
    if user.role == Role.ADMIN:
        return stmt
    if user.role == Role.INSTITUTION:
        return stmt.where(ReviewCase.institution_id == user.institution_id)
    return stmt.where(ReviewCase.requested_by == user.id)


def list_cases(
    db: Session, user: User, *, status: str | None = None, page: int, size: int
) -> tuple[list[ReviewCase], int]:
    """Newest activity first, scoped to what this user may see."""
    stmt = _scope(select(ReviewCase), user)
    if status == "open":
        stmt = stmt.where(ReviewCase.status != ReviewStatus.CLOSED.value)
    elif status:
        if status not in {s.value for s in ReviewStatus}:
            raise AppError(422, "invalid_status", f"Unknown status {status!r}.")
        stmt = stmt.where(ReviewCase.status == status)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.scalars(
        stmt.order_by(ReviewCase.updated_at.desc(), ReviewCase.id)
        .offset((page - 1) * size)
        .limit(size)
    ).all()
    return list(items), total


def counts(db: Session, user: User) -> dict[str, int]:
    """Open and overdue counts for the nav badge and the admin card."""
    stale_before = datetime.now(UTC) - timedelta(days=STALE_DAYS)
    open_stmt = _scope(select(ReviewCase), user).where(
        ReviewCase.status != ReviewStatus.CLOSED.value
    )
    return {
        "open": db.scalar(select(func.count()).select_from(open_stmt.subquery())) or 0,
        "open_over_7_days": db.scalar(
            select(func.count()).select_from(
                open_stmt.where(ReviewCase.created_at < stale_before).subquery()
            )
        )
        or 0,
    }


# --- creating a request -------------------------------------------------------


def _verification_for_request(db: Session, user: User, verification_id: uuid.UUID) -> Verification:
    verification = db.get(Verification, verification_id)
    if verification is None or verification.verifier_id != user.id:
        # Only the verifier who ran it may escalate it, and another
        # verifier's result is indistinguishable from one that does not
        # exist — the same rule `verifications.get_verification` applies.
        raise AppError(404, "not_found", "Verification not found.")
    if verification.result not in ESCALATABLE_RESULTS:
        raise AppError(
            409,
            "not_escalatable",
            "Only a result that needs review or shows a mismatch can be sent to an institution.",
        )
    return verification


def _institution_for(db: Session, verification: Verification, institution_id: int | None) -> int:
    """Which institution to ask.

    The record's own institution when the document identified one — the
    verifier should not be able to send a known certificate to the wrong
    institution. Otherwise the verifier picks, and it must be an active one.
    """
    if verification.certificate is not None:
        return verification.certificate.institution_id
    if institution_id is None:
        raise AppError(
            422,
            "institution_required",
            "This document did not identify an institution, so one has to be chosen.",
        )
    institution = db.get(Institution, institution_id)
    if institution is None or not institution.is_active:
        raise AppError(422, "institution_invalid", "That institution cannot receive requests.")
    return institution.id


def create_case(
    db: Session,
    user: User,
    *,
    verification_id: uuid.UUID,
    institution_id: int | None = None,
    note: str | None = None,
) -> ReviewCase:
    """Open a request about a verification. One open case per verification."""
    verification = _verification_for_request(db, user, verification_id)
    target = _institution_for(db, verification, institution_id)

    case = ReviewCase(
        id=uuid.uuid4(),
        verification_id=verification.id,
        institution_id=target,
        requested_by=user.id,
        status=ReviewStatus.PENDING.value,
        note=(note or "").strip() or None,
    )
    db.add(case)
    audit.record(
        db,
        actor_id=user.id,
        action="review.create",
        entity="review_case",
        entity_id=str(case.id),
        meta={
            "verification_id": str(verification.id),
            "institution_id": target,
            "result": verification.result,
            "has_note": case.note is not None,
        },
    )
    try:
        db.commit()
    except IntegrityError as exc:
        # The partial unique index: someone already has this verification open.
        db.rollback()
        raise AppError(
            409,
            "request_already_open",
            "A request about this verification is already open with the institution.",
        ) from exc
    db.refresh(case)
    return case


def open_case_for(db: Session, verification_id: uuid.UUID) -> ReviewCase | None:
    """The open case about a verification, if there is one. Used to decide
    whether the result page offers the button or shows the request."""
    return db.scalar(
        select(ReviewCase)
        .where(
            ReviewCase.verification_id == verification_id,
            ReviewCase.status != ReviewStatus.CLOSED.value,
        )
        .limit(1)
    )


def cases_for_verification(db: Session, verification_id: uuid.UUID) -> list[ReviewCase]:
    """Every case about a verification, newest first — the result page shows
    the decision beside the original result."""
    return list(
        db.scalars(
            select(ReviewCase)
            .where(ReviewCase.verification_id == verification_id)
            .order_by(ReviewCase.created_at.desc())
        )
    )


# --- the thread ---------------------------------------------------------------


def _may_write(case: ReviewCase, user: User) -> bool:
    """An admin reads; the two parties write."""
    if user.role == Role.ADMIN:
        return False
    return _visible(case, user)


def add_message(db: Session, user: User, case_id: uuid.UUID, body: str) -> ReviewMessage:
    """Reply on a case. Either party may; a closed case takes no more."""
    case = get_case(db, user, case_id)
    if not _may_write(case, user):
        raise AppError(403, "forbidden", "You cannot reply to this request.")
    if not case.is_open:
        raise AppError(409, "case_closed", "This request is closed.")

    text = body.strip()
    if not text:
        raise AppError(422, "message_empty", "A reply needs some text.")

    message = ReviewMessage(id=uuid.uuid4(), case_id=case.id, author_id=user.id, body=text)
    db.add(message)
    # A verifier answering a question puts the ball back in the institution's
    # court, which is what `needs_info -> pending` means.
    if case.status == ReviewStatus.NEEDS_INFO.value and user.role != Role.INSTITUTION:
        case.status = ReviewStatus.PENDING.value
    case.updated_at = datetime.now(UTC)
    audit.record(
        db,
        actor_id=user.id,
        action="review.message",
        entity="review_case",
        entity_id=str(case.id),
        meta={"message_id": str(message.id), "status": case.status},
    )
    db.commit()
    db.refresh(message)
    return message


def ask_for_info(db: Session, user: User, case_id: uuid.UUID, body: str) -> ReviewCase:
    """The institution asks the verifier for more: one message, one status
    change, one transaction."""
    case = _institution_case(db, user, case_id)
    text = body.strip()
    if not text:
        raise AppError(422, "message_empty", "Say what you need from the verifier.")

    message = ReviewMessage(id=uuid.uuid4(), case_id=case.id, author_id=user.id, body=text)
    db.add(message)
    case.status = ReviewStatus.NEEDS_INFO.value
    case.updated_at = datetime.now(UTC)
    audit.record(
        db,
        actor_id=user.id,
        action="review.needs_info",
        entity="review_case",
        entity_id=str(case.id),
        meta={"verification_id": str(case.verification_id), "message_id": str(message.id)},
    )
    db.commit()
    db.refresh(case)
    return case


# --- deciding -----------------------------------------------------------------


def _institution_case(db: Session, user: User, case_id: uuid.UUID) -> ReviewCase:
    """A case this institution user is entitled to act on, still open."""
    if user.role != Role.INSTITUTION or user.institution_id is None:
        raise AppError(403, "forbidden", "Only the institution asked can answer a request.")
    case = get_case(db, user, case_id)
    if case.institution_id != user.institution_id:  # pragma: no cover - get_case scopes it
        raise AppError(404, "not_found", "Verification request not found.")
    if not case.is_open:
        raise AppError(409, "case_closed", "This request has already been answered.")
    return case


def _close(
    db: Session,
    user: User,
    case: ReviewCase,
    decision: ReviewDecision,
    *,
    decision_note: str | None,
    meta: dict[str, object] | None = None,
) -> ReviewCase:
    case.status = ReviewStatus.CLOSED.value
    case.decision = decision.value
    case.decision_note = (decision_note or "").strip() or None
    case.decided_by = user.id
    case.decided_at = datetime.now(UTC)
    case.updated_at = case.decided_at
    audit.record(
        db,
        actor_id=user.id,
        action=f"review.{decision.value}",
        entity="review_case",
        entity_id=str(case.id),
        meta={
            "verification_id": str(case.verification_id),
            "institution_id": case.institution_id,
            **(meta or {}),
        },
    )
    db.commit()
    db.refresh(case)
    return case


def confirm(db: Session, user: User, case_id: uuid.UUID, *, note: str | None = None) -> ReviewCase:
    """The institution confirms the document is genuine as presented."""
    case = _institution_case(db, user, case_id)
    return _close(db, user, case, ReviewDecision.CONFIRMED, decision_note=note)


def not_issued(db: Session, user: User, case_id: uuid.UUID, *, reason: str) -> ReviewCase:
    """The institution states it has no such record.

    A reason is required: this is the one answer a holder may be harmed by, so
    it does not get to be a bare flag.
    """
    case = _institution_case(db, user, case_id)
    if not reason.strip():
        raise AppError(422, "reason_required", "Say on what basis the record was not found.")
    return _close(db, user, case, ReviewDecision.NOT_ISSUED, decision_note=reason)


def confirm_and_add(
    db: Session, user: User, case_id: uuid.UUID, fields: CertificateFields
) -> tuple[ReviewCase, Certificate]:
    """Confirm, and add the certificate the registry was missing.

    Goes through `certificates.create_certificate`, so the row is signed with
    the institution's key and gets its issued PDF exactly like any other —
    there is no second way into the registry. The certificate is created
    first: if it fails (a duplicate number, a missing signing key) the case
    stays open and the institution can correct the form.
    """
    case = _institution_case(db, user, case_id)
    cert = certificates.create_certificate(db, user, fields)
    return (
        _close(
            db,
            user,
            case,
            ReviewDecision.CONFIRMED_ADDED,
            decision_note=None,
            meta={"certificate_id": str(cert.id), "cert_number": cert.cert_number},
        ),
        cert,
    )


# --- what the institution needs to see ----------------------------------------


def registry_match(db: Session, case: ReviewCase) -> Certificate | None:
    """The institution's own record for this document, if it has one.

    The verification may have found none — that is usually why the request
    exists — so the number read off the page is tried against this
    institution's rows. Scoped to the institution on the case: a request must
    never surface another institution's record.
    """
    if case.verification.certificate is not None:
        return case.verification.certificate
    extracted = case.verification.extracted_fields or {}
    number = extracted.get("cert_number")
    if not number:
        return None
    return db.scalar(
        select(Certificate).where(
            Certificate.cert_number == number,
            Certificate.institution_id == case.institution_id,
        )
    )


def prefill(case: ReviewCase, match: Certificate | None) -> dict[str, object]:
    """A starting point for the "confirm & add" form.

    What the document said, as the OCR read it, with the document's own casing
    (`raw`) rather than the normalized comparison form — an institution is
    correcting a draft, not reading our internals. Nothing here is trusted:
    every field is editable and validated on submit like any other create.
    """
    if match is not None:
        return {}
    extracted = (case.verification.extracted_fields or {}).get("fields") or {}
    out: dict[str, object] = {}
    for name, found in extracted.items():
        raw = (found or {}).get("raw") or (found or {}).get("value")
        if raw:
            out[name] = raw
    return out


__all__ = [
    "ESCALATABLE_RESULTS",
    "STALE_DAYS",
    "add_message",
    "ask_for_info",
    "cases_for_verification",
    "confirm",
    "confirm_and_add",
    "counts",
    "create_case",
    "get_case",
    "list_cases",
    "not_issued",
    "open_case_for",
    "prefill",
    "registry_match",
]
