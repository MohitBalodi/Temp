"""Verification requests: look the record up, run the engine, keep the evidence.

The decision itself lives in `verification/engine.py` and stays pure — this
module only does the I/O around it (lookup, persistence, audit).
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import Certificate, Role, User, Verification
from app.services import audit
from app.services.qr import QrPayload, QrPayloadError, parse_payload
from app.services.signing import CertificateRecord
from app.services.verification.engine import (
    RegistryRecord,
    VerificationInput,
    VerificationMethod,
    evaluate,
)


def _registry_record(cert: Certificate) -> RegistryRecord:
    """Map the stored row onto the facts the engine checks."""
    return RegistryRecord(
        record=CertificateRecord(
            cert_number=cert.cert_number,
            institution_code=cert.institution.code,
            student_name=cert.student_name,
            roll_number=cert.roll_number,
            programme=cert.programme,
            year_of_passing=cert.year_of_passing,
            cgpa=cert.cgpa,
            marks=cert.marks,
            issue_date=cert.issue_date,
        ),
        signature=cert.signature,
        public_key_pem=cert.institution.public_key,
        status=cert.status,
        revoked_at=cert.revoked_at,
    )


def _lookup(db: Session, cert_number: str) -> Certificate | None:
    """Any institution's certificate: a verifier is not scoped to one registry."""
    return db.scalar(select(Certificate).where(Certificate.cert_number == cert_number))


def _run(
    db: Session,
    user: User,
    *,
    method: VerificationMethod,
    cert_number: str,
    qr: QrPayload | None,
) -> Verification:
    cert = _lookup(db, cert_number)
    outcome = evaluate(
        VerificationInput(
            method=method,
            cert_number=cert_number,
            record=_registry_record(cert) if cert else None,
            qr=qr,
        )
    )

    queried: dict[str, str] = {"cert_number": cert_number}
    if qr is not None:
        queried["institution_code"] = qr.institution_code

    verification = Verification(
        id=uuid.uuid4(),
        verifier_id=user.id,
        method=method.value,
        certificate_id=cert.id if cert else None,
        result=outcome.result.value,
        checks=outcome.checks_as_dicts(),
        extracted_fields=queried,
    )
    db.add(verification)
    audit.record(
        db,
        actor_id=user.id,
        action="verification.create",
        entity="verification",
        entity_id=str(verification.id),
        meta={
            "method": method.value,
            "result": outcome.result.value,
            "cert_number": cert_number,
            "certificate_id": str(cert.id) if cert else None,
        },
    )
    db.commit()
    db.refresh(verification)
    return verification


def verify_by_number(db: Session, user: User, cert_number: str) -> Verification:
    return _run(db, user, method=VerificationMethod.ID, cert_number=cert_number, qr=None)


def verify_by_payload(db: Session, user: User, payload: str) -> Verification:
    """Verify a scanned QR. An unreadable payload is a bad request, not a
    verdict on a document, so nothing is recorded for it."""
    try:
        qr = parse_payload(payload)
    except QrPayloadError as exc:
        raise AppError(
            422, "qr_payload_invalid", f"This is not a certificate QR code: {exc}"
        ) from exc
    return _run(db, user, method=VerificationMethod.QR, cert_number=qr.cert_number, qr=qr)


def get_verification(db: Session, user: User, verification_id: uuid.UUID) -> Verification:
    """The verifier who ran it, or an admin. Same answer for absent and other
    people's verifications."""
    verification = db.get(Verification, verification_id)
    if verification is None or (user.role != Role.ADMIN and verification.verifier_id != user.id):
        raise AppError(404, "not_found", "Verification not found.")
    return verification
