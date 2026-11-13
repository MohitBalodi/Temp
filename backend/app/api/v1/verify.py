import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.deps import DbSession, require_role
from app.models import Role, User, Verification
from app.schemas.common import Page
from app.schemas.verify import (
    VerificationListItem,
    VerificationOut,
    VerifyByIdRequest,
    VerifyByQrRequest,
)
from app.services import verifications as service

router = APIRouter(prefix="/verify", tags=["verify"])
verifications_router = APIRouter(prefix="/verifications", tags=["verify"])

Verifier = Annotated[User, Depends(require_role(Role.VERIFIER, Role.ADMIN))]


@router.post("/id", response_model=VerificationOut)
def verify_by_id(body: VerifyByIdRequest, user: Verifier, db: DbSession) -> Verification:
    """Verify by certificate number. Always returns a result with its evidence;
    an unknown number is MANUAL_REVIEW, never an accusation."""
    return service.verify_by_number(db, user, body.cert_number)


@router.post(
    "/qr",
    response_model=VerificationOut,
    responses={422: {"description": "The payload is not a certificate QR code"}},
)
def verify_by_qr(body: VerifyByQrRequest, user: Verifier, db: DbSession) -> Verification:
    """Verify a scanned QR payload: the signature it carries is re-checked
    against the registry record and the institution's public key."""
    return service.verify_by_payload(db, user, body.payload)


@verifications_router.get("", response_model=Page[VerificationListItem])
def list_verifications(
    user: Verifier,
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Page[VerificationListItem]:
    """Verification history, newest first: your own, or all of them for an admin."""
    items, total = service.list_verifications(db, user, page=page, size=size)
    return Page[VerificationListItem](
        items=[VerificationListItem.model_validate(v) for v in items],
        total=total,
        page=page,
        size=size,
    )


@verifications_router.get("/{verification_id}", response_model=VerificationOut)
def get_verification(verification_id: uuid.UUID, user: Verifier, db: DbSession) -> Verification:
    return service.get_verification(db, user, verification_id)
