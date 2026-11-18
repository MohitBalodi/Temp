"""Verification requests: `/reviews`.

Who may do what is decided in `services/reviews.py`, not here — the router
only says which roles may reach an endpoint at all. The finer rule (an
institution sees only what was addressed to it, a verifier only their own) is
a scoping question, and scoping belongs with the query.
"""

import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse

from app.core.deps import CurrentUser, DbSession, require_role
from app.core.errors import AppError
from app.models import ReviewCase, Role, User
from app.schemas.common import Page
from app.schemas.reviews import (
    ConfirmAndAddDecision,
    ConfirmDecision,
    DecisionRequest,
    MessageCreate,
    MessageOut,
    NotIssuedDecision,
    ReviewCounts,
    ReviewCreate,
    ReviewListItem,
    ReviewOut,
)
from app.services import reviews

router = APIRouter(prefix="/reviews", tags=["reviews"])

# Verifiers open requests; institutions answer them; admins only read. Every
# role reaches the list and the detail, and the service scopes what they see.
Verifier = Annotated[User, Depends(require_role(Role.VERIFIER))]
Institution = Annotated[User, Depends(require_role(Role.INSTITUTION))]


def _as_list_item(case: ReviewCase) -> ReviewListItem:
    return ReviewListItem(
        id=case.id,
        verification_id=case.verification_id,
        cert_number=case.verification.cert_number,
        result=case.verification.result,
        institution=case.institution,  # type: ignore[arg-type]
        requester=case.requester,  # type: ignore[arg-type]
        status=case.status,
        decision=case.decision,
        created_at=case.created_at,
        updated_at=case.updated_at,
    )


def _as_detail(db: DbSession, case: ReviewCase, user: User) -> ReviewOut:
    """One case, with only what this viewer is entitled to.

    The verification is included because the institution has to judge what was
    presented, and the prefilled draft only when there is no record to match —
    a registry that already holds the certificate needs no new row.
    """
    match = reviews.registry_match(db, case)
    is_the_institution = (
        user.role == Role.INSTITUTION and case.institution_id == user.institution_id
    )
    document = _document_path(case)
    return ReviewOut(
        id=case.id,
        verification_id=case.verification_id,
        cert_number=case.verification.cert_number,
        institution=case.institution,  # type: ignore[arg-type]
        requester=case.requester,  # type: ignore[arg-type]
        status=case.status,
        note=case.note,
        decision=case.decision,
        decision_note=case.decision_note,
        decider=case.decider,  # type: ignore[arg-type]
        decided_at=case.decided_at,
        created_at=case.created_at,
        updated_at=case.updated_at,
        messages=[MessageOut.model_validate(m) for m in case.messages],
        verification=case.verification,  # type: ignore[arg-type]
        registry_match=match,  # type: ignore[arg-type]
        prefill={k: str(v) for k, v in reviews.prefill(case, match).items()},
        document_available=document is not None,
        can_decide=is_the_institution and case.is_open,
        can_reply=user.role != Role.ADMIN and case.is_open,
    )


def _document_path(case: ReviewCase) -> Path | None:
    upload = case.verification.upload
    if upload is None:
        return None
    path = Path(upload.path)
    return path if path.is_file() else None


@router.post("", response_model=ReviewOut, status_code=201)
def create_review(body: ReviewCreate, user: Verifier, db: DbSession) -> ReviewOut:
    """Ask an institution to confirm a verification the system could not settle."""
    case = reviews.create_case(
        db,
        user,
        verification_id=body.verification_id,
        institution_id=body.institution_id,
        note=body.note,
    )
    return _as_detail(db, case, user)


@router.get("", response_model=Page[ReviewListItem])
def list_reviews(
    user: CurrentUser,
    db: DbSession,
    status: Annotated[str | None, Query(description="pending | needs_info | closed | open")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Page[ReviewListItem]:
    """Requests this user may see, most recently updated first."""
    items, total = reviews.list_cases(db, user, status=status, page=page, size=size)
    return Page[ReviewListItem](
        items=[_as_list_item(c) for c in items], total=total, page=page, size=size
    )


@router.get("/counts", response_model=ReviewCounts)
def review_counts(user: CurrentUser, db: DbSession) -> ReviewCounts:
    """Open and overdue counts, scoped like the list: the nav badge and the
    admin dashboard card both read this."""
    return ReviewCounts(**reviews.counts(db, user))


@router.get("/{case_id}", response_model=ReviewOut)
def get_review(case_id: uuid.UUID, user: CurrentUser, db: DbSession) -> ReviewOut:
    return _as_detail(db, reviews.get_case(db, user, case_id), user)


@router.get(
    "/{case_id}/document",
    response_class=FileResponse,
    responses={404: {"description": "No document, or it is no longer stored"}},
)
def get_review_document(case_id: uuid.UUID, user: CurrentUser, db: DbSession) -> FileResponse:
    """The uploaded document itself, for the institution to look at.

    This is the one place a document a verifier uploaded leaves the
    verification pipeline, and it is the point of the feature: an institution
    cannot confirm a certificate it is not allowed to see. Scoped exactly like
    the case, so only the institution asked, the verifier who asked, and an
    admin can fetch it. `inline` so a browser previews rather than downloads.
    """
    case = reviews.get_case(db, user, case_id)
    path = _document_path(case)
    if path is None:
        raise AppError(404, "document_unavailable", "The uploaded document is no longer stored.")
    return FileResponse(
        path,
        media_type=case.verification.upload.mime,
        content_disposition_type="inline",
        filename=f"{case.verification.cert_number or 'document'}{path.suffix}",
    )


@router.post("/{case_id}/messages", response_model=MessageOut, status_code=201)
def post_message(
    case_id: uuid.UUID, body: MessageCreate, user: CurrentUser, db: DbSession
) -> MessageOut:
    """Reply on a case. A verifier answering a `needs_info` question puts it
    back to `pending`."""
    return MessageOut.model_validate(reviews.add_message(db, user, case_id, body.body))


@router.post("/{case_id}/needs-info", response_model=ReviewOut)
def ask_for_info(
    case_id: uuid.UUID, body: MessageCreate, user: Institution, db: DbSession
) -> ReviewOut:
    """The institution asks the verifier for more before answering."""
    return _as_detail(db, reviews.ask_for_info(db, user, case_id, body.body), user)


@router.post("/{case_id}/decision", response_model=ReviewOut)
def decide(
    case_id: uuid.UUID,
    body: DecisionRequest,
    user: Institution,
    db: DbSession,
) -> ReviewOut:
    """Answer a request. Closes the case; the verification is left untouched."""
    if isinstance(body, ConfirmDecision):
        case = reviews.confirm(db, user, case_id, note=body.note)
    elif isinstance(body, ConfirmAndAddDecision):
        case, _ = reviews.confirm_and_add(db, user, case_id, body.certificate)
    elif isinstance(body, NotIssuedDecision):
        case = reviews.not_issued(db, user, case_id, reason=body.reason)
    else:  # pragma: no cover - the union is exhaustive
        raise AppError(422, "unknown_decision", "Unknown decision.")
    return _as_detail(db, case, user)
