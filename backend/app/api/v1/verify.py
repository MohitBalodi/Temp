import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, UploadFile

from app.core.deps import DbSession, require_role
from app.models import Role, User, Verification
from app.schemas.common import Page
from app.schemas.verify import (
    JobStatusOut,
    UploadAccepted,
    VerificationListItem,
    VerificationOut,
    VerifyByIdRequest,
    VerifyByQrRequest,
)
from app.services import upload_jobs, uploads
from app.services import verifications as service

router = APIRouter(prefix="/verify", tags=["verify"])
verifications_router = APIRouter(prefix="/verifications", tags=["verify"])

Verifier = Annotated[User, Depends(require_role(Role.VERIFIER, Role.ADMIN))]

# Upload bodies are streamed in chunks of this size, never read whole first.
_READ_CHUNK_BYTES = 256 * 1024


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


@router.post(
    "/upload",
    response_model=UploadAccepted,
    status_code=202,
    responses={
        413: {"description": "The file is over the size limit"},
        415: {"description": "The file's own bytes are not PDF, PNG or JPEG"},
    },
)
async def verify_by_upload(
    user: Verifier,
    db: DbSession,
    file: Annotated[UploadFile, File(description="A PDF, PNG or JPEG certificate, max 10 MB.")],
) -> UploadAccepted:
    """Upload a certificate for OCR verification.

    Returns at once with a job to poll: extraction runs in the worker. The
    file's type is decided by its leading bytes, not by its name or the
    Content-Type the client sent.
    """
    data = await _read_capped(file)
    return upload_jobs.submit(db, data, user)


async def _read_capped(file: UploadFile) -> bytes:
    """Read at most one byte past the limit.

    Streaming rather than `file.read()` so an oversized body is refused
    without being held in memory in full. The one extra byte is what makes
    "exactly at the limit" and "over it" distinguishable; `uploads.store`
    raises the 413.
    """
    limit = uploads.max_bytes()
    chunks: list[bytes] = []
    total = 0
    while chunk := await file.read(_READ_CHUNK_BYTES):
        chunks.append(chunk)
        total += len(chunk)
        if total > limit:
            break
    return b"".join(chunks)[: limit + 1]


@router.get("/jobs/{job_id}", response_model=JobStatusOut)
def get_job(job_id: str, user: Verifier) -> JobStatusOut:
    """Poll an upload job. `done` carries the verification id to fetch."""
    return upload_jobs.status(job_id, user)


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
