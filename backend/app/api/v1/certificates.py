import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, UploadFile, status
from fastapi.responses import FileResponse

from app.core.deps import DbSession, require_role
from app.models import Certificate, Role, User
from app.schemas.certificates import (
    CertificateCreate,
    CertificateOut,
    ImportErrorResponse,
    ImportResult,
    RevokeRequest,
)
from app.schemas.common import Page
from app.services import certificates as service

router = APIRouter(prefix="/certificates", tags=["certificates"])

InstitutionUser = Annotated[User, Depends(require_role(Role.INSTITUTION))]
RegistryReader = Annotated[User, Depends(require_role(Role.INSTITUTION, Role.ADMIN))]


@router.post("", response_model=CertificateOut, status_code=status.HTTP_201_CREATED)
def create_certificate(
    body: CertificateCreate, user: InstitutionUser, db: DbSession
) -> Certificate:
    return service.create_certificate(db, user, body)


@router.post(
    "/import",
    response_model=ImportResult,
    responses={422: {"model": ImportErrorResponse, "description": "Per-row CSV errors"}},
)
def import_certificates(file: UploadFile, user: InstitutionUser, db: DbSession) -> ImportResult:
    content = file.file.read()
    return ImportResult(imported=service.import_csv(db, user, content, file.filename))


@router.get("", response_model=Page[CertificateOut])
def list_certificates(
    user: RegistryReader,
    db: DbSession,
    q: Annotated[str | None, Query(max_length=100, description="Search number, roll, name")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Page[CertificateOut]:
    items, total = service.list_certificates(db, user, q=q, page=page, size=size)
    return Page[CertificateOut](
        items=[CertificateOut.model_validate(c) for c in items], total=total, page=page, size=size
    )


@router.get("/{certificate_id}", response_model=CertificateOut)
def get_certificate(certificate_id: uuid.UUID, user: RegistryReader, db: DbSession) -> Certificate:
    return service.get_certificate(db, user, certificate_id)


@router.post(
    "/{certificate_id}/revoke",
    response_model=CertificateOut,
    responses={
        404: {"description": "Not this institution's certificate"},
        409: {"description": "Already revoked"},
    },
)
def revoke_certificate(
    certificate_id: uuid.UUID, body: RevokeRequest, user: InstitutionUser, db: DbSession
) -> Certificate:
    """Revoke one of your own certificates. Verification then reports REVOKED."""
    return service.revoke_certificate(db, user, certificate_id, body.reason)


@router.get(
    "/{certificate_id}/pdf",
    response_class=FileResponse,
    responses={
        200: {"content": {"application/pdf": {}}, "description": "The issued certificate PDF"},
        404: {"description": "Certificate not found, or no PDF stored for it"},
    },
)
def get_certificate_pdf(
    certificate_id: uuid.UUID, user: RegistryReader, db: DbSession
) -> FileResponse:
    """Serve the PDF generated when the certificate was issued, byte for byte,
    so its SHA-256 still matches `file_sha256`. It is never regenerated."""
    cert = service.get_certificate(db, user, certificate_id)
    return FileResponse(
        service.issued_pdf(cert),
        media_type="application/pdf",
        filename=f"{cert.cert_number}.pdf",
        headers={"X-Certificate-SHA256": cert.file_sha256 or ""},
    )
